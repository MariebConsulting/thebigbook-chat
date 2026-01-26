from app.rag.vectorstore import LanceVectorStore

if __name__ == "__main__":
    LanceVectorStore().reset()
    print("✅ LanceDB table reset.")
