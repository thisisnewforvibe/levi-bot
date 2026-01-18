"""
Extract Uzbek vocabulary from PDF book to improve Whisper transcription.
"""

import PyPDF2
import re
from collections import Counter
from pathlib import Path

def extract_text_from_pdf(pdf_path):
    """Extract all text from PDF file."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"📖 Reading {len(pdf_reader.pages)} pages...")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                text += page_text + "\n"
                if page_num % 10 == 0:
                    print(f"   Processed {page_num} pages...")
    
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return None
    
    print(f"✅ Extracted {len(text)} characters")
    return text


def extract_uzbek_words(text):
    """Extract common Uzbek words and phrases."""
    # Remove numbers, special characters, keep Uzbek letters
    words = re.findall(r"[a-zA-Zo'ʻ'`]+", text.lower())
    
    # Count word frequencies
    word_freq = Counter(words)
    
    # Get most common words (excluding very short ones)
    common_words = [
        word for word, count in word_freq.most_common(300)
        if len(word) >= 3 and count >= 3
    ]
    
    return common_words


def create_whisper_prompt(words, max_length=224):
    """
    Create initial prompt for Whisper (max 224 tokens).
    Focus on reminder-related vocabulary.
    """
    # Priority words for reminders
    priority_keywords = [
        'minut', 'minutdan', 'soat', 'soatdan', 'keyin', 'kun', 
        'ertaga', 'bugun', 'eslat', 'eslatma', 'qil', 'qilish',
        'kerak', 'kerак', 'o\'qish', 'namoz', 'kitob', 'dars',
        'ish', 'ishga', 'bor', 'borish', 'kel', 'kelish',
        'yoz', 'yozish', 'telefon', 'qo\'ng\'iroq', 'xabar',
        'uchrash', 'yig\'ilish', 'vaqt', 'payt'
    ]
    
    # Filter words that appear in both our priority list and the book
    relevant_words = []
    for keyword in priority_keywords:
        matches = [w for w in words if keyword in w or w in keyword]
        relevant_words.extend(matches[:5])  # Max 5 variations per keyword
    
    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for word in relevant_words:
        if word not in seen:
            seen.add(word)
            unique_words.append(word)
    
    # Add general common Uzbek words from book
    book_words = [w for w in words if w not in unique_words][:100]
    unique_words.extend(book_words)
    
    # Create prompt text (space-separated)
    prompt = " ".join(unique_words[:150])  # Limit to ~150 words
    
    # Ensure it's under 224 characters (Whisper's limit)
    if len(prompt) > max_length:
        words_list = prompt.split()
        prompt = " ".join(words_list[:50])  # Reduce to 50 words
    
    return prompt


def main():
    """Main extraction process."""
    # Process all three Uzbek books
    pdf_paths = [
        Path(__file__).parent / "uzbek_book.pdf",          # Dialect research book (216 pages)
        Path(__file__).parent / "uzbek_dictionary.pdf",    # Official Uzbek dictionary (441 pages)
        Path(__file__).parent / "uzbek_grammar.pdf"        # Uzbek grammar book
    ]
    output_path = Path(__file__).parent / "uzbek_vocabulary.txt"
    
    print("🎯 Extracting Uzbek vocabulary from multiple PDFs...")
    
    all_words = []
    
    # Extract from each PDF
    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            print(f"⚠️  Skipping {pdf_path.name} (not found)")
            continue
            
        print(f"\n📄 Processing: {pdf_path.name}")
        
        # Extract text
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"❌ Failed to extract text from {pdf_path.name}")
            continue
        
        # Extract words
        print(f"📝 Analyzing vocabulary...")
        words = extract_uzbek_words(text)
        all_words.extend(words)
        print(f"✅ Found {len(words)} common Uzbek words")
    
    # Combine and deduplicate
    print(f"\n🔄 Merging vocabularies...")
    unique_words = list(dict.fromkeys(all_words))  # Preserve order, remove duplicates
    print(f"✅ Total unique words: {len(unique_words)}")
    
    # Create Whisper prompt from combined vocabulary
    prompt = create_whisper_prompt(unique_words)
    print(f"\n✅ Created Whisper prompt ({len(prompt)} chars)")
    print(f"Preview: {prompt[:200]}...")
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"\n💾 Saved to: {output_path}")
    print("\n🎯 Next steps:")
    print("1. Bot will automatically use this vocabulary")
    print("2. Test with voice message")
    print("3. Transcription should be much more accurate!")


if __name__ == "__main__":
    main()
