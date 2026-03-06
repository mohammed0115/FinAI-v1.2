"""
Performance Monitoring & Metrics Collection
Tracks execution time and performance of invoice processing pipeline
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, Callable
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Collect and track performance metrics"""
    
    _metrics: Dict[str, list] = {}
    
    @classmethod
    def record(cls, metric_name: str, duration: float, metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        if metric_name not in cls._metrics:
            cls._metrics[metric_name] = []
        
        record = {
            'timestamp': datetime.now().isoformat(),
            'duration': duration,
            'metadata': metadata or {},
        }
        
        cls._metrics[metric_name].append(record)
        
        # Keep only last 1000 records per metric
        if len(cls._metrics[metric_name]) > 1000:
            cls._metrics[metric_name] = cls._metrics[metric_name][-1000:]
        
        logger.info(f"Performance: {metric_name} = {duration:.3f}s")
    
    @classmethod
    def get_stats(cls, metric_name: str) -> Dict[str, Any]:
        """Get statistics for a metric"""
        if metric_name not in cls._metrics or not cls._metrics[metric_name]:
            return {}
        
        durations = [m['duration'] for m in cls._metrics[metric_name]]
        
        return {
            'metric': metric_name,
            'count': len(durations),
            'min': min(durations),
            'max': max(durations),
            'avg': sum(durations) / len(durations),
            'total': sum(durations),
            'last': durations[-1] if durations else None,
        }
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all metrics"""
        return {metric: cls.get_stats(metric) for metric in cls._metrics}
    
    @classmethod
    def print_report(cls):
        """Print performance report"""
        print("\n" + "="*80)
        print("PERFORMANCE METRICS REPORT")
        print("="*80)
        
        for metric, stats in cls.get_all_stats().items():
            if not stats:
                continue
            
            print(f"\n{metric}:")
            print(f"  Calls: {stats['count']}")
            print(f"  Min:   {stats['min']:.3f}s")
            print(f"  Max:   {stats['max']:.3f}s")
            print(f"  Avg:   {stats['avg']:.3f}s")
            print(f"  Total: {stats['total']:.3f}s")
            print(f"  Last:  {stats['last']:.3f}s")
        
        print("\n" + "="*80 + "\n")
    
    @classmethod
    def reset(cls):
        """Reset all metrics"""
        cls._metrics = {}


def track_performance(metric_name: str = None):
    """Decorator to track function execution time"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            name = metric_name or f"{func.__module__}.{func.__name__}"
            
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                PerformanceMetrics.record(name, duration)
        
        return wrapper
    
    return decorator


class PipelineExecutionMonitor:
    """Monitor complete pipeline execution"""
    
    def __init__(self, invoice_id: str = None):
        self.invoice_id = invoice_id
        self.phase_times = {}
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start monitoring"""
        self.start_time = time.time()
    
    def end(self):
        """End monitoring"""
        self.end_time = time.time()
    
    def record_phase(self, phase_name: str, duration: float):
        """Record time for specific phase"""
        self.phase_times[phase_name] = duration
        logger.info(f"Phase {phase_name}: {duration:.3f}s")
    
    def get_total_time(self) -> float:
        """Get total execution time"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def print_report(self):
        """Print execution report"""
        print("\n" + "-"*60)
        print(f"Pipeline Execution Report (Invoice: {self.invoice_id})")
        print("-"*60)
        
        for phase, duration in self.phase_times.items():
            percentage = (duration / self.get_total_time() * 100) if self.get_total_time() > 0 else 0
            bar = "█" * int(percentage / 5)
            print(f"  {phase:<25} {duration:>7.3f}s [{bar:<20}] {percentage:>5.1f}%")
        
        print("-"*60)
        print(f"  Total Time: {self.get_total_time():.3f}s")
        print("-"*60 + "\n")


# Global monitors
_monitors: Dict[str, PipelineExecutionMonitor] = {}


def get_monitor(invoice_id: str) -> PipelineExecutionMonitor:
    """Get or create monitor for invoice"""
    if invoice_id not in _monitors:
        _monitors[invoice_id] = PipelineExecutionMonitor(invoice_id)
    return _monitors[invoice_id]


def cleanup_monitors():
    """Clean up old monitors"""
    global _monitors
    _monitors = {}


# Logging configuration for performance tracking
def setup_performance_logging():
    """Setup detailed performance logging"""
    
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler for performance logs
    try:
        file_handler = logging.FileHandler('logs/performance.log')
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not setup file logging: {e}")
    
    logger.addHandler(console_handler)
