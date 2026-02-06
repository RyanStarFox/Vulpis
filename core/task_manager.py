import threading
import time

# Global dictionary to store tasks
# Since this is a local app, we can use a simple global dict.
# Structure: { task_id: { "type": str, "status": str, "message": str, "progress": float, "result": Any } }
TASKS = {}

def get_tasks():
    return TASKS

def start_indexing_task(kb_name, filenames, kb_manager_cls):
    """
    Start a background thread to index files.
    kb_manager_cls: The KBManager class (passed to avoid circular imports or re-instantiation issues)
    """
    task_id = f"indexing_{kb_name}_{int(time.time())}"
    
    TASKS[task_id] = {
        "type": "indexing",
        "status": "running",
        "message": "准备开始处理...",
        "progress": 0.0,
        "kb_name": kb_name
    }
    
    def worker():
        try:
            # Instantiate a new manager in this thread
            manager = kb_manager_cls()
            total = len(filenames)
            
            for i, filename in enumerate(filenames):
                TASKS[task_id]["message"] = f"正在处理: {filename}"
                TASKS[task_id]["progress"] = i / total
                
                # Perform the heavy lifting
                try:
                    manager.add_single_file_to_index(kb_name, filename)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    # We continue despite errors
            
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["message"] = "处理完成"
            TASKS[task_id]["progress"] = 1.0
            
            # Auto-clean completed tasks after 10 seconds (optional, but good for UI)
            # time.sleep(10)
            # if task_id in TASKS:
            #    del TASKS[task_id]
                
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["message"] = f"任务失败: {str(e)}"
            print(f"Task failed: {e}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return task_id

def start_import_folder_task(kb_name, source_dir, kb_manager_cls):
    """
    Start a background thread to import a folder.
    """
    task_id = f"import_{kb_name}_{int(time.time())}"
    
    TASKS[task_id] = {
        "type": "importing",
        "status": "running",
        "message": "正在扫描文件夹...",
        "progress": 0.0,
        "kb_name": kb_name
    }
    
    def worker():
        try:
            manager = kb_manager_cls()
            # We need to modify import_from_directory to be granular or just run it blindly.
            # Standard import_from_directory does everything.
            # To get progress, we might need to duplicate logic or add a callback.
            # For now, let's just run it and show "processing".
            # Or better: We assume import_from_directory is "fast enough" per file but total time is long.
            # But import_from_directory includes the loop.
            
            # Let's delegate to the existing method, but we won't get granular progress 
            # unless we refactor import_from_directory to accept a progress callback.
            # For MVP, just run it.
            
            TASKS[task_id]["message"] = f"正在导入 {source_dir}..."
            count, errs = manager.import_from_directory(kb_name, source_dir)
            
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["message"] = f"导入完成: 成功 {count}, 失败 {errs}"
            TASKS[task_id]["progress"] = 1.0
            
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["message"] = f"导入失败: {str(e)}"

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return task_id

def start_rebuild_task(kb_name, kb_manager_cls):
    """
    Start a background thread to rebuild the KB index.
    """
    task_id = f"rebuild_{kb_name}_{int(time.time())}"
    
    TASKS[task_id] = {
        "type": "rebuild",
        "status": "running",
        "message": "正在重建索引 (可能需要较长时间)...",
        "progress": 0.0,
        "kb_name": kb_name
    }
    
    def worker():
        try:
            manager = kb_manager_cls()
            # rebuild_kb_index operations
            manager.rebuild_kb_index(kb_name)
            
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["message"] = "索引重建完成"
            TASKS[task_id]["progress"] = 1.0
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["message"] = f"重建失败: {str(e)}"
            print(f"Rebuild task failed: {e}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return task_id

def start_update_index_task(kb_name, kb_manager_cls):
    """
    Start a background thread to update KB index incrementally.
    """
    task_id = f"update_{kb_name}_{int(time.time())}"
    
    TASKS[task_id] = {
        "type": "update",
        "status": "running",
        "message": "正在检测变更...",
        "progress": 0.0,
        "kb_name": kb_name
    }
    
    def worker():
        try:
            manager = kb_manager_cls()
            TASKS[task_id]["message"] = "正在同步索引..."
            TASKS[task_id]["progress"] = 0.3
            
            added, removed = manager.update_kb_index(kb_name)
            
            TASKS[task_id]["status"] = "completed"
            if added == 0 and removed == 0:
                TASKS[task_id]["message"] = "索引已是最新"
            else:
                TASKS[task_id]["message"] = f"同步完成：+{added}, -{removed}"
            TASKS[task_id]["progress"] = 1.0
            TASKS[task_id]["result"] = {"added": added, "removed": removed}
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["message"] = f"更新失败: {str(e)}"
            print(f"Update task failed: {e}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return task_id


def start_upload_task(kb_name, uploaded_files_data, kb_manager_cls):
    """
    Start a background thread to process uploaded files.
    uploaded_files_data: list of tuples [(filename, file_bytes), ...]
    """
    task_id = f"upload_{kb_name}_{int(time.time())}"
    
    TASKS[task_id] = {
        "type": "upload",
        "status": "running",
        "message": "准备上传文件...",
        "progress": 0.0,
        "kb_name": kb_name,
        "total_files": len(uploaded_files_data),
        "processed_files": 0
    }
    
    def worker():
        import os
        from core.config import DATA_DIR
        try:
            manager = kb_manager_cls()
            total = len(uploaded_files_data)
            
            for i, (filename, file_bytes) in enumerate(uploaded_files_data):
                TASKS[task_id]["message"] = f"正在处理: {filename} ({i+1}/{total})"
                TASKS[task_id]["progress"] = i / total
                TASKS[task_id]["processed_files"] = i
                
                # Save file to disk
                kb_path = os.path.join(DATA_DIR, kb_name)
                if not os.path.exists(kb_path):
                    os.makedirs(kb_path)
                file_path = os.path.join(kb_path, filename)
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                
                # Add to index
                try:
                    manager.add_single_file_to_index(kb_name, filename)
                except Exception as e:
                    print(f"Error indexing {filename}: {e}")
            
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["message"] = f"上传完成: {total} 个文件"
            TASKS[task_id]["progress"] = 1.0
            TASKS[task_id]["processed_files"] = total
            
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["message"] = f"上传失败: {str(e)}"
            print(f"Upload task failed: {e}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return task_id


def get_kb_active_tasks(kb_name):
    """Get all active (running) tasks for a specific KB."""
    return {
        k: v for k, v in TASKS.items() 
        if v.get("kb_name") == kb_name and v["status"] == "running"
    }


def get_kb_recent_tasks(kb_name, max_age_seconds=30):
    """Get recent completed/failed tasks for a KB (within max_age_seconds)."""
    import time as t
    current = t.time()
    result = {}
    for k, v in TASKS.items():
        if v.get("kb_name") == kb_name and v["status"] in ["completed", "failed"]:
            # Check task age from task_id timestamp
            try:
                task_time = int(k.split("_")[-1])
                if current - task_time < max_age_seconds:
                    result[k] = v
            except:
                pass
    return result


def clear_completed_tasks():
    to_remove = [k for k, v in TASKS.items() if v["status"] in ["completed", "failed"]]
    for k in to_remove:
        del TASKS[k]
