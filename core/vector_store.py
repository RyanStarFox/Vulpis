import os
from typing import List, Dict

import chromadb
from chromadb.config import Settings
from openai import OpenAI
from tqdm import tqdm

from core import config

import hashlib
import pickle
from rank_bm25 import BM25Okapi
import jieba
from chromadb.utils import embedding_functions
from datetime import datetime
from core.settings_utils import get_user_data_dir

class VectorStore:

    def __init__(self, collection_name="knowledge_base"):
        self.collection_name = collection_name
        
        # Use user data directory for persistence (Cross-platform)
        data_dir = get_user_data_dir()
        self.persist_directory = os.path.join(data_dir, "chroma_db")

        # 初始化OpenAI客户端
        self.client = config.get_openai_client(api_key=config.EMBEDDING_API_KEY, base_url=config.EMBEDDING_API_BASE)

        # 初始化ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_directory
        )

        # 安全处理 Collection Name (支持中文等特殊字符)
        # ChromaDB 只允许 3-63 字符，且只能包含字母数字、下划线、短横线
        # 我们使用 MD5 哈希来映射任意名称到合法的 Collection Name
        self.original_collection_name = collection_name
        
        # 即使是英文，使用哈希也是更安全的策略，避免长度超标或非法字符
        # 但为了保留可读性 (如 Default_KB)，我们可以简单检查一下
        import re
        if re.match(r'^[a-zA-Z0-9_-]{3,63}$', collection_name):
            self.safe_collection_name = collection_name
        else:
            # 对于非法名称 (如中文)，使用哈希值
            hash_name = hashlib.md5(collection_name.encode('utf-8')).hexdigest()
            self.safe_collection_name = f"kb_{hash_name}"
            # 注意：这意味着如果用户删除了 vector_db 文件夹但没有删除 data 文件夹，
            # 重新生成的哈希值应该是一样的，所以能找回。

        # 获取或创建collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.safe_collection_name, metadata={"description": "课程材料向量数据库", "original_name": collection_name}
        )
        
        # BM25 Cache Path setup
        cache_dir = os.path.join(data_dir, "bm25_cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        self.bm25_cache_path = os.path.join(cache_dir, f"{self.safe_collection_name}.pkl")

        # 混合检索初始化
        self.enable_hybrid = config.ENABLE_HYBRID_SEARCH
        print(f"[VectorStore] 初始化完成。混合检索(Hybrid Search): {self.enable_hybrid}")
        
        self.bm25 = None
        self.doc_ids = []
        self.doc_contents = []
        self.doc_metadatas = []
        
        if self.enable_hybrid:
            self._build_bm25_index()

    def _clear_bm25_cache(self):
        """清除本地 BM25 缓存文件"""
        try:
            if os.path.exists(self.bm25_cache_path):
                os.remove(self.bm25_cache_path)
        except Exception as e:
            print(f"Warning: Failed to clear BM25 cache: {e}")

    def _build_bm25_index(self, force_rebuild=False):
        """构建BM25索引 (支持持久化缓存)"""
        try:
            print(f"[BM25] [{self.safe_collection_name}] 开始初始化索引流程...")
            
            # 1. 尝试从缓存加载
            if not force_rebuild:
                print(f"[BM25] 正在检查缓存文件: {self.bm25_cache_path}")
                if os.path.exists(self.bm25_cache_path):
                    try:
                        print(f"[BM25] ✅ 发现缓存文件，正在加载...")
                        start_load = datetime.now()
                        with open(self.bm25_cache_path, "rb") as f:
                            cache_data = pickle.load(f)
                        
                        # 校验缓存有效性
                        current_count = self.collection.count()
                        cache_count = len(cache_data["ids"])
                        
                        if cache_count == current_count:
                            self.bm25 = cache_data["bm25"]
                            self.doc_ids = cache_data["ids"]
                            self.doc_contents = cache_data["contents"]
                            self.doc_metadatas = cache_data["metadatas"]
                            print(f"[BM25] ✅ 缓存加载成功！耗时: {datetime.now() - start_load}")
                            print(f"       包含 {len(self.doc_contents)} 条文档。")
                            return
                        else:
                            print(f"[BM25] ⚠️ 缓存失效: 缓存文档数({cache_count}) != 当前数据库文档数({current_count})")
                            print("[BM25] 触发强制重建...")
                    except Exception as e:
                        print(f"[BM25] ❌ 缓存加载出错: {e}，将触发重建...")
                else:
                    print(f"[BM25] ❌ 未找到缓存文件，准备开始构建...")
            else:
                 print(f"[BM25] 收到强制重建指令...")

            # 2. 从数据库构建
            print(f"[BM25] 开始从向量数据库读取所有文档 (可能需要几秒钟)...")
            start_read = datetime.now()
            all_docs = self.collection.get(include=["documents", "metadatas"])
            
            if not all_docs["ids"]:
                print("[BM25] ⚠️ 知识库为空，跳过索引构建")
                self.bm25 = None
                return
                
            self.doc_ids = all_docs["ids"]
            self.doc_contents = all_docs["documents"]
            self.doc_metadatas = all_docs["metadatas"]
            print(f"[BM25] 文档读取完成！共 {len(self.doc_contents)} 条，耗时: {datetime.now() - start_read}")
            
            print(f"[BM25] 开始分词并构建倒排索引...")
            start_build = datetime.now()
            tokenized_corpus = [list(jieba.cut(doc)) for doc in self.doc_contents]
            self.bm25 = BM25Okapi(tokenized_corpus)
            print(f"[BM25] 内存索引构建完成，耗时: {datetime.now() - start_build}")
            
            # 3. 保存缓存
            try:
                print(f"[BM25] 正在将缓存写入磁盘 (首次写入较慢，请耐心等待)...")
                start_save = datetime.now()
                with open(self.bm25_cache_path, "wb") as f:
                    cache_data = {
                        "bm25": self.bm25,
                        "ids": self.doc_ids,
                        "contents": self.doc_contents,
                        "metadatas": self.doc_metadatas
                    }
                    pickle.dump(cache_data, f)
                print(f"[BM25] ✅ 缓存写入成功！耗时: {datetime.now() - start_save}")
                print(f"[BM25] 🎉 索引构建全流程结束。")
            except Exception as e:
                print(f"[BM25] ❌ 缓存写入失败: {e}")

        except Exception as e:
            print(f"[BM25] ❌ 索引构建严重失败: {e}")
            self.enable_hybrid = False

    def get_embedding(self, text: str) -> List[float]:
        """获取文本的向量表示"""
        import time
        
        # 调用OpenAI API获取embedding
        # 增加重试机制以解决超时问题
        max_retries = 3
        current_timeout = 60.0
        
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=config.OPENAI_EMBEDDING_MODEL,
                    input=text,
                    timeout=current_timeout
                )
                return response.data[0].embedding
            except Exception as e:
                # 包含超时错误 (APITimeoutError)
                if attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)
                    print(f"Embedding API 请求失败 (尝试 {attempt+1}/{max_retries}): {e}。等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    # 最后一次尝试也失败，抛出异常
                    raise e

    def add_documents(self, chunks: List[Dict[str, str]]) -> None:
        """添加文档块到向量数据库
        TODO: 实现文档块添加到向量数据库
        要求：
        1. 遍历文档块
        2. 获取文档块内容
        3. 获取文档块元数据
        5. 打印添加进度
        """
        if not chunks:
            return
        documents = []
        embeddings = []
        metadatas = []
        ids = []

        # 遍历文档块，准备数据
        for chunk in tqdm(chunks, desc="添加文档到向量数据库", unit="块"):
            # 获取文档块内容
            content = chunk.get("content", "")
            if not content:
                continue

            # 获取文档块元数据
            metadata = {
                "filename": chunk.get("filename", "unknown"),
                "filepath": chunk.get("filepath", ""),
                "filetype": chunk.get("filetype", ""),
                "page_number": str(chunk.get("page_number", 0)),
                "chunk_id": str(chunk.get("chunk_id", 0)),
            }

            # === 修改开始 ===
            chunk_id = chunk.get("chunk_id", 0)
            page_number = chunk.get("page_number", 0)
            filename = chunk.get("filename", "unknown")
            filepath = chunk.get("filepath", "")
            
            # 使用文件路径生成哈希，解决同名文件冲突问题
            path_hash = hashlib.md5(filepath.encode('utf-8')).hexdigest()[:6]
            unique_id = f"{filename}_{path_hash}_p{page_number}_c{chunk_id}"
            # === 修改结束 ===

            embedding = self.get_embedding(content)

            documents.append(content)
            embeddings.append(embedding)
            metadatas.append(metadata)
            ids.append(unique_id)

        if documents:
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"\n成功添加 {len(documents)} 个文档块到向量数据库")
            
            if self.enable_hybrid:
                print("正在更新 BM25 索引...")
                self._clear_bm25_cache() # 强制清除缓存
                self._build_bm25_index(force_rebuild=True)

    def search(self, query: str, top_k: int = None) -> Dict:
        """搜索相关文档 (支持混合检索)"""
        if top_k is None:
            top_k = config.TOP_K

        if not self.enable_hybrid or not self.bm25:
            # 仅使用向量检索
            embedding = self.get_embedding(query)
            results = self.collection.query(
                query_embeddings=embedding,
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            return results
        
        # 混合检索策略：Weighted Reciprocal Rank Fusion (Weighted RRF)
        # 1. 向量检索召回
        embedding = self.get_embedding(query)
        # 扩大召回数量以便重排序
        fetch_k = min(top_k * 2, len(self.doc_ids)) if len(self.doc_ids) > 0 else top_k
        if fetch_k == 0: return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        vec_results = self.collection.query(
            query_embeddings=embedding,
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # 2. BM25检索召回
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        # 获取 top N 的索引
        bm25_top_n_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:fetch_k]
        
        # 3. 融合排名
        # 使用 RRF 算法: score = alpha * (1 / (k + rank_vec)) + (1 - alpha) * (1 / (k + rank_bm25))
        # k 通常取 60
        rrf_k = 60
        alpha = config.HYBRID_SEARCH_ALPHA
        
        # 构建文档 ID 到排名的映射
        vec_rank_map = {} # doc_id -> rank (0-based)
        if vec_results['ids'] and vec_results['ids'][0]:
            for rank, doc_id in enumerate(vec_results['ids'][0]):
                vec_rank_map[doc_id] = rank

        bm25_rank_map = {} # doc_id -> rank (0-based)
        for rank, idx in enumerate(bm25_top_n_indices):
            doc_id = self.doc_ids[idx]
            bm25_rank_map[doc_id] = rank
            
        # 收集所有涉及的文档 ID
        all_candidate_ids = set(vec_rank_map.keys()) | set(bm25_rank_map.keys())
        
        final_scores = []
        for doc_id in all_candidate_ids:
            # 获取向量排名 (如果没有出现，假设排在最后)
            rank_vec = vec_rank_map.get(doc_id, fetch_k + rrf_k)
            # 获取BM25排名
            rank_bm25 = bm25_rank_map.get(doc_id, fetch_k + rrf_k)
            
            score = alpha * (1 / (rrf_k + rank_vec + 1)) + (1 - alpha) * (1 / (rrf_k + rank_bm25 + 1))
            final_scores.append((doc_id, score))
            
        # 排序并取 Top K
        final_scores.sort(key=lambda x: x[1], reverse=True)
        top_results = final_scores[:top_k]
        
        # 4. 格式化输出 (模拟 Chroma 格式)
        res_ids = []
        res_docs = []
        res_metas = []
        res_scores = []
        
        # 为了快速查找 content 和 metadata，建立索引映射
        id_to_idx = {did: i for i, did in enumerate(self.doc_ids)}
        
        for doc_id, score in top_results:
            if doc_id in id_to_idx:
                idx = id_to_idx[doc_id]
                res_ids.append(doc_id)
                res_docs.append(self.doc_contents[idx])
                res_metas.append(self.doc_metadatas[idx])
                res_scores.append(score) # 注意这里返回的是混合分数
                
        return {
            "ids": [res_ids],
            "documents": [res_docs],
            "metadatas": [res_metas],
            "distances": [res_scores] # 兼容 agent 逻辑，虽然名字叫 distance 但这里是 score
        }

    def delete_collection(self, collection_name: str) -> None:
        """删除指定的collection"""
        # 同样需要进行哈希转换
        import re
        if re.match(r'^[a-zA-Z0-9_-]{3,63}$', collection_name):
            safe_name = collection_name
        else:
            safe_name = f"kb_{hashlib.md5(collection_name.encode('utf-8')).hexdigest()}"

        try:
            self.chroma_client.delete_collection(name=safe_name)
            # Remove BM25 Cache
            cache_path = os.path.join(os.path.dirname(self.bm25_cache_path), f"{safe_name}.pkl")
            if os.path.exists(cache_path):
                os.remove(cache_path)
            print(f"Collection {collection_name} (safe: {safe_name}) 已删除")
        except Exception as e:
            print(f"删除 Collection {collection_name} 失败 (可能不存在): {e}")

    def clear_collection(self) -> None:
        """清空collection"""
        # 使用 self.safe_collection_name
        try:
            self.chroma_client.delete_collection(name=self.safe_collection_name)
        except:
            pass # Ignore if doesn't exist
            
        self.collection = self.chroma_client.create_collection(
            name=self.safe_collection_name, 
            metadata={"description": "课程向量数据库", "original_name": self.original_collection_name}
        )
        print("向量数据库已清空")
        self._clear_bm25_cache()

    def get_collection_count(self) -> int:
        """获取collection中的文档数量"""
        return self.collection.count()
    
    def delete_documents_by_file(self, filename: str) -> int:
        """删除指定文件的所有文档块
        
        Args:
            filename: 文件名（不含路径）
            
        Returns:
            删除的文档数量
        """
        try:
            # 查询该文件的所有文档
            all_docs = self.collection.get(
                where={"filename": filename},
                include=["metadatas"]
            )
            
            if not all_docs["ids"]:
                print(f"未找到文件 {filename} 的文档")
                return 0
            
            # 删除这些文档
            doc_ids = all_docs["ids"]
            self.collection.delete(ids=doc_ids)
            
            deleted_count = len(doc_ids)
            print(f"已删除文件 {filename} 的 {deleted_count} 个文档块")
            
            # 重建 BM25 索引
            if self.enable_hybrid:
                self._clear_bm25_cache()
                self._build_bm25_index(force_rebuild=True)
            
            return deleted_count
        except Exception as e:
            print(f"删除文件文档时出错: {e}")
            return 0
    def delete_documents_by_filepath(self, filepath: str) -> int:
        """根据文件绝对路径删除文档块"""
        try:
            # Query by filepath metadata
            all_docs = self.collection.get(
                where={"filepath": filepath},
                include=["metadatas"]
            )
            if not all_docs["ids"]:
                return 0
            
            doc_ids = all_docs["ids"]
            self.collection.delete(ids=doc_ids)
            
            # Rebuild BM25 if needed
            if self.enable_hybrid:
                self._clear_bm25_cache()
                self._build_bm25_index(force_rebuild=True)
                
            return len(doc_ids)
        except Exception as e:
            print(f"Error deleting by filepath: {e}")
            return 0

    def get_existing_files(self) -> set:
        """获取数据库中已存在的所有文件的路径 (filepath)"""
        try:
            # Get all metadatas only
            all_data = self.collection.get(include=["metadatas"])
            if not all_data["metadatas"]:
                return set()
            
            # Return set of filepaths
            return set(
                m.get("filepath", "") 
                for m in all_data["metadatas"] 
                if m.get("filepath")
            )
        except Exception as e:
            print(f"Error getting existing files: {e}")
            return set()
