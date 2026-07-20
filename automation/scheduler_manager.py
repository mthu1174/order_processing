import threading
import time
from datetime import datetime

class SchedulerManager:
    def __init__(self, config_manager, trigger_callback, log_callback):
        self.config_manager = config_manager
        self.trigger_callback = trigger_callback # Generic function to start automation
        self.log = log_callback
        self.is_running = False
        self._thread = None
        self._last_triggered = {} # To avoid multiple triggers in the same minute
        self._change_event = threading.Event()

    def notify_change(self):
        """Wake up the scheduler loop because something in the config changed"""
        self._change_event.set()

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            self.log("[HỆ THỐNG] Trình lập lịch (Scheduler) đã khởi động.")

    def stop(self):
        self.is_running = False

    def _loop(self):
        while self.is_running:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                current_date = now.strftime("%Y-%m-%d")
                
                schedules = self.config_manager.get("schedules", [])
                
                for sched in schedules:
                    if not sched.get("enabled", True):
                        continue
                    
                    sched_time = sched["time"]
                    task_name = sched["task"]
                    
                    # Check if matches and wasn't triggered today at this time
                    trigger_key = f"{sched['id']}_{current_date}_{sched_time}"
                    
                    if current_time == sched_time and trigger_key not in self._last_triggered:
                        self.log(f"[HẸN GIỜ] Kích hoạt tác vụ: {task_name}")
                        self._last_triggered[trigger_key] = True
                        
                        # Trigger the work in a separate thread to not block the scheduler
                        # We pass both the task name and the ID to ensure uniqueness if needed
                        threading.Thread(target=self.trigger_callback, args=(task_name,), daemon=True).start()
                
                # Clean up old triggers from _last_triggered to save memory
                if len(self._last_triggered) > 100:
                    # Keep only today's triggers (simple cleanup)
                    self._last_triggered = {k: v for k, v in self._last_triggered.items() if current_date in k}

            except Exception as e:
                self.log(f"[LỖI SCHEDULER] {e}")
            
            # TÍNH TOÁN THỜI GIAN NGỦ
            # Mặc định ngủ 1 tiếng nếu không có lịch
            wait_time = 3600 
            
            try:
                now = datetime.now()
                schedules = self.config_manager.get("schedules", [])
                enabled_schedules = [s for s in schedules if s.get("enabled", True)]
                
                if enabled_schedules:
                    future_waits = []
                    for s in enabled_schedules:
                        # Parse HH:MM
                        h, m = map(int, s["time"].split(":"))
                        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        
                        # Nếu giờ đã qua trong hôm nay, tính cho ngày mai
                        if target <= now:
                            from datetime import timedelta
                            target += timedelta(days=1)
                        
                        diff = (target - now).total_seconds()
                        future_waits.append(diff)
                    
                    if future_waits:
                        wait_time = min(future_waits)
                        # Đảm bảo tỉnh dậy sớm hơn 1-2 giây để chính xác
                        wait_time = max(1, wait_time - 1) 
            except: pass

            # NGỦ NGẮT QUÃNG:
            # Sẽ ngủ wait_time giây, HOẶC tỉnh dậy ngay lập tức nếu self.notify_change() được gọi
            self._change_event.clear()
            self._change_event.wait(timeout=wait_time)
