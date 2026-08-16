from src.document_processor import MarkdownProcessor

processor = MarkdownProcessor("knowledge_base/meridian_wealth/")
docs = processor.process_all()

for doc in docs:
    preview = doc["content"][:200].replace("\n", " ")
    print(f"[{doc['filename']}]")
    print(f"  {preview}")
    print()

print(f"Total files processed: {len(docs)}")
