import os
import json
import sys
import openpyxl

# Set standard output encoding to utf-8 safely
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
RAW_PATH = os.path.join('data', 'raw', 'iValue_Solution_Recommendation_Dataset.xlsx')
EXCEL_PATH = RAW_PATH if os.path.exists(RAW_PATH) else 'iValue_Solution_Recommendation_Dataset.xlsx'
OUTPUT_JSON_PATH = 'data/composite_products.json'

def clean_sentence_end(text: str) -> str:
    """Ensure clean punctuation without trailing double periods or weird whitespace."""
    if not text:
        return ""
    cleaned = " ".join(str(text).split()).strip()
    if cleaned.endswith("."):
        return cleaned
    return cleaned + "."

def clean_clause(text: str) -> str:
    """Clean statement for list items (pros/cons/features). Remove trailing punctuation."""
    if not text:
        return ""
    cleaned = " ".join(str(text).split()).strip()
    return cleaned.rstrip(".;,")

def sheet_to_dicts(sheet):
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return [], []
    headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
    data = []
    for r in rows[1:]:
        if all(cell is None for cell in r):
            continue
        row_dict = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
        data.append(row_dict)
    return headers, data

def main():
    print("================================================================")
    print("   iValue Presales Automation - Composite Text Builder (FR-18)  ")
    print("================================================================")
    print(f"Reading dataset from: {EXCEL_PATH}...")

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    _, prod_rows = sheet_to_dicts(wb['Products'])
    _, feat_rows = sheet_to_dicts(wb['Product_Features'])
    _, pros_rows = sheet_to_dicts(wb['Product_Pros_Cons'])

    # Group features by Product_ID
    features_by_pid = {}
    for f in feat_rows:
        pid = f.get('Product_ID')
        fname = clean_clause(f.get('Feature_Name', ''))
        if pid and fname:
            features_by_pid.setdefault(pid, []).append(fname)

    # Group Pros and Cons by Product_ID
    pros_by_pid = {}
    cons_by_pid = {}
    for pc in pros_rows:
        pid = pc.get('Product_ID')
        statement = clean_clause(pc.get('Statement', ''))
        t = str(pc.get('Type', '')).strip().lower()
        if not pid or not statement:
            continue
        if 'pro' in t or 'advantage' in t:
            pros_by_pid.setdefault(pid, []).append(statement)
        else:
            cons_by_pid.setdefault(pid, []).append(statement)

    composite_records = []
    warnings = []

    for p in prod_rows:
        pid = p.get('Product_ID')
        pname = str(p.get('Product_Name', '')).strip()
        oem = str(p.get('OEM_Name', '')).strip()
        domain = str(p.get('Domain_Category', '')).strip()
        sub_domain = str(p.get('Sub_Domain', '')).strip()
        category = str(p.get('Product_Category', '')).strip()
        desc = clean_sentence_end(p.get('What_Is_It', ''))
        use_case = clean_sentence_end(p.get('Primary_Use_Case', ''))
        customer = clean_sentence_end(p.get('Ideal_Customer_Profile', ''))
        diff = clean_sentence_end(p.get('Key_Differentiator', ''))
        deployment = clean_sentence_end(p.get('Deployment_Model', ''))

        feats = features_by_pid.get(pid, [])
        pros = pros_by_pid.get(pid, [])
        cons = cons_by_pid.get(pid, [])

        feats_str = ", ".join(feats) + "." if feats else "None listed."
        pros_str = "; ".join(pros) + "." if pros else "None listed."
        cons_str = "; ".join(cons) + "." if cons else "None listed."

        # Assemble strictly according to SRS Section 4.4 template
        composite_text = (
            f"{pname} by {oem}.\n"
            f"Domain: {domain} / {sub_domain}.\n"
            f"Category: {category}.\n"
            f"Description: {desc}\n"
            f"Primary use case: {use_case}\n"
            f"Ideal customer: {customer}\n"
            f"Key differentiator: {diff}\n"
            f"Deployment: {deployment}\n"
            f"Features: {feats_str}\n"
            f"Strengths: {pros_str}\n"
            f"Limitations: {cons_str}"
        )

        char_count = len(composite_text)
        word_count = len(composite_text.split())
        approx_tokens = int(word_count * 1.33)  # standard rule of thumb for English

        if approx_tokens > 512:
            warnings.append((pid, pname, approx_tokens))

        composite_records.append({
            "product_id": pid,
            "oem_name": oem,
            "product_name": pname,
            "domain_category": domain,
            "sub_domain": sub_domain,
            "product_category": category,
            "data_status": p.get('Data_Status', 'Draft'),
            "last_verified": str(p.get('Last_Verified', '')),
            "source_url": str(p.get('Source_URL', '')),
            "features": feats,
            "strengths": pros,
            "limitations": cons,
            "composite_text": composite_text,
            "char_count": char_count,
            "word_count": word_count,
            "approx_tokens": approx_tokens
        })

    print(f"\nSuccessfully constructed composite text for {len(composite_records)} products.")
    
    # Token length statistics
    token_counts = [r['approx_tokens'] for r in composite_records]
    print("\n--- Composite Text Token Statistics (bge-small 512 context limit) ---")
    print(f"  Min tokens:     {min(token_counts)}")
    print(f"  Max tokens:     {max(token_counts)}")
    print(f"  Average tokens: {sum(token_counts)/len(token_counts):.1f}")
    
    if warnings:
        print(f"\n  [WARNING] {len(warnings)} products exceed 512 tokens:")
        for pid, name, tok in warnings:
            print(f"    - {pid} ({name}): ~{tok} tokens")
    else:
        print("  [PASS] 100% of products fit comfortably within the 512-token context limit!")

    # Save to data/composite_products.json
    os.makedirs('data', exist_ok=True)
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(composite_records, f, indent=2, ensure_ascii=False)
    print(f"\nExported composite products dataset to: {OUTPUT_JSON_PATH}")

    # Print 2 diverse samples
    print("\n--- Sample 1: " + composite_records[0]['product_name'] + " (" + composite_records[0]['product_id'] + ") ---")
    print(composite_records[0]['composite_text'])
    print(f"Word count: {composite_records[0]['word_count']}, Approx tokens: {composite_records[0]['approx_tokens']}")

    print("\n--- Sample 2: " + composite_records[65]['product_name'] + " (" + composite_records[65]['product_id'] + ") ---")
    print(composite_records[65]['composite_text'])
    print(f"Word count: {composite_records[65]['word_count']}, Approx tokens: {composite_records[65]['approx_tokens']}")

    print("\n================================================================")
    print("[SUCCESS] Composite text pipeline completed successfully.")
    print("================================================================")

if __name__ == "__main__":
    main()
