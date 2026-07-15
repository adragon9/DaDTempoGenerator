import time

class PerformanceMonitor():
    def __init__(self):
        pass
    
    def start_monitor(self):
        self.stime = time.perf_counter()
    
    def end_monitor(self):
        self.etime = time.perf_counter()
    
    def get_performance(self):
        if not self.stime:
            return "Start time not established!"
        elif not self.etime:
            return "End time not established!"
        
        return self.etime - self.stime
