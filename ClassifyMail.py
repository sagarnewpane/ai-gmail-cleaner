import sqlite3
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import re
import time
import hashlib

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def fetch_unclassified(limit=50, db='emails.db'):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender, subject, snippet FROM emails WHERE category IS NULL LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def anonymize_email_content(text):
    """Anonymize potentially sensitive content to reduce recitation risk"""
    # Replace email addresses with placeholders
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    # Replace URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[URL]', text)
    # Replace phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    # Replace potential account numbers/IDs
    text = re.sub(r'\b\d{8,}\b', '[ACCOUNT_NUM]', text)
    return text

def classify_emails(rows, batch_id=None):
    """
    Classify a list of email rows using Gemini API with improved anti-recitation strategies.
    """
    # Strategy 1: Add randomization to reduce pattern matching
    import random
    batch_suffix = f"_batch_{batch_id or random.randint(1000, 9999)}"
    
    emails_data = []
    for i, row in enumerate(rows, start=1):
        email_id, sender, subject, snippet = row
        
        # Strategy 2: Anonymize and truncate content
        snippet_text = anonymize_email_content(snippet or "No content")[:200]
        sender_clean = anonymize_email_content(sender)[:100]
        subject_clean = anonymize_email_content(subject or "No subject")[:150]
        
        emails_data.append({
            'num': i,
            'from': sender_clean,
            'subj': subject_clean,
            'text': snippet_text
        })

    # Strategy 3: Use more abstract/analytical prompt style
    prompt = f"""
Task: Email Priority Analysis {batch_suffix}

Analyze these email metadata samples and determine priority level:
- HIGH: Work deadlines, personal urgent matters, financial/security alerts, meeting invites
- LOW: Marketing content, newsletters, social updates, automated notices

Output format: number,priority_level
Use only HIGH or LOW as priority_level values.

Data samples:
"""
    
    for email in emails_data:
        prompt += f"\n{email['num']}. From: {email['from']} | Subject: {email['subj']} | Content: {email['text']}"
    
    prompt += f"\n\nAnalysis{batch_suffix}:"

    # Strategy 4: Multiple retry attempts with different approaches
    for attempt in range(3):
        try:
            # Vary temperature slightly between attempts
            temp = 0.1 + (attempt * 0.1)
            generation_config = genai.types.GenerationConfig(
                temperature=temp,
                top_p=0.8,
                top_k=20
            )
            
            safety_settings = [
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE,
                },
            ]

            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            if not response.candidates:
                print(f"[WARNING] Attempt {attempt+1}: No candidates returned")
                time.sleep(1)  # Brief delay before retry
                continue

            candidate = response.candidates[0]
            
            # Check finish reason
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
                print(f"Finish reason: {finish_reason}")
                
                if finish_reason == 4:  # RECITATION
                    print(f"[WARNING] Attempt {attempt+1}: RECITATION detected, retrying with modified prompt...")
                    # Modify prompt for next attempt
                    prompt = prompt.replace(batch_suffix, f"_retry_{attempt}_{random.randint(100, 999)}")
                    time.sleep(2)
                    continue

            if not candidate.content.parts:
                print(f"[WARNING] Attempt {attempt+1}: No content parts")
                continue

            classifications = candidate.content.parts[0].text.strip()
            
            if classifications:
                # Convert HIGH/LOW back to IMPORTANT/NOT IMPORTANT
                classifications = classifications.replace("HIGH", "IMPORTANT").replace("LOW", "NOT IMPORTANT")
                return classifications
                
        except Exception as e:
            print(f"[WARNING] Attempt {attempt+1} failed:", str(e))
            time.sleep(2)
    
    return "\n".join(fallback_results)

def update_classifications(rows, classifications, db='emails.db'):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # More flexible regex to handle different formats
    matches = re.findall(r"^\s*(\d+)\s*[,:]\s*(IMPORTANT|NOT IMPORTANT|HIGH|LOW)\s*$", 
                        classifications, re.MULTILINE | re.IGNORECASE)

    updated_count = 0
    for match in matches:
        try:
            idx_str, label = match
            idx = int(idx_str.strip()) - 1  # 0-based index
            label = label.strip().upper()
            
            # Convert HIGH/LOW to IMPORTANT/NOT IMPORTANT if needed
            if label == "HIGH":
                label = "IMPORTANT"
            elif label == "LOW":
                label = "NOT IMPORTANT"

            if 0 <= idx < len(rows):
                email_id = rows[idx][0]
                cursor.execute("UPDATE emails SET category = ? WHERE id = ?", (label, email_id))
                updated_count += 1
            else:
                print(f"[WARNING] Index {idx+1} out of range")
        except Exception as e:
            print(f"[WARNING] Error processing: {match}, Error: {e}")

    conn.commit()
    conn.close()
    print(f"[SUCCESS] Updated {updated_count} email classifications")

def main():
    # Process smaller batches to reduce recitation risk
    batch_size = 10
    batch_count = 0
    
    while True:
        rows = fetch_unclassified(limit=batch_size, db='emails.db')
        if not rows:
            print("[SUCCESS] All emails are classified")
            break

        batch_count += 1
        print(f"\n[INFO] Processing batch {batch_count} ({len(rows)} emails)")
        
        classifications = classify_emails(rows, batch_id=batch_count)
        print("Classifications received:")
        print(classifications)
        
        update_classifications(rows, classifications, db='emails.db')
        
        # Brief pause between batches
        time.sleep(1)

if __name__ == "__main__":
    main()