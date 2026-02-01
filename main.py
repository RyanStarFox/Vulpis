import os
from core.rag_agent import RAGAgent

from core.config import VECTOR_DB_PATH, MODEL_NAME


def main():

    if not os.path.exists(VECTOR_DB_PATH):
        return

    # 初始化RAG Agent
    agent = RAGAgent(model=MODEL_NAME)

    # 检查知识库
    count = agent.vector_store.get_collection_count()
    if count == 0:
        return

    agent.chat()


if __name__ == "__main__":
    main()
