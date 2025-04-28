from PySide6.QtCore import QThread, QObject, Signal, Slot

class WorkerSignals(QObject):
    finished = Signal()
    result = Signal(object)
    error = Signal(Exception)

class Worker(QObject):
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.function(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self.signals.finished.emit()

class ThreadManager:
    def __init__(self):
        self.threads = []

    def run_function(self, function, *args, **kwargs):
        # Create thread and worker
        thread = QThread()
        worker = Worker(function, *args, **kwargs)
        worker.moveToThread(thread)

        # Connect signals
        thread.started.connect(worker.run)
        worker.signals.finished.connect(thread.quit)
        worker.signals.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.threads.remove((thread, worker)))

        # Store thread reference
        self.threads.append((thread, worker))

        # Start thread
        thread.start()
        return worker.signals

    def cleanup(self):
        # Only cleanup threads that are still running
        for thread, _ in self.threads[:]:
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)
        
        self.threads.clear()