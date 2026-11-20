"""
Implement the first readers-writers algorithm with semaphores.  This is the 1st problem in the slides

> Readers may share access however a writer holds the lock alone. 
> The first active reader blocks writers for the reader group and the final reader releases them. 
> New readers may continue joining ahead of a waiting writer, so a steady stream of readers can keep the writing waiting 
indefinitely.  This is the first readers-writers problem, which favors readers over writers.

"""
# Threading module proovides a Semaphore class that can be used to implement the readers-writers algorithm.
import threading


class RWLock:
    def __init__(self):
        # Protect changes to the shared count of active readers.
        self._mutex = threading.Semaphore(1)
        # Number of readers currently in the critical section.
        self._read_count = 0
        # Writers take this semaphore; the reader group holds it as a unit.
        self._wrt = threading.Semaphore(1)

    """Join the reader group, waiting if a writer currently holds access."""
    def acquire_read(self):
        # The reader locks the counter
        self._mutex.acquire()
        # Increment the count of active readers. 
        self._read_count += 1
        # If this is the first reader, it blocks writers from entering until the group empties.
        # If writers holds the lock, the first reader will be blocked here until the writer releases it.
        if self._read_count == 1:
            self._wrt.acquire()
        # Release the counter lock so other readers may join the group.
        self._mutex.release()

    """Leave the reader group and unblock writers when the last reader exits."""
    def release_read(self):
        # The reader locks the counter
        self._mutex.acquire()
        # Decrement the count of active readers.
        self._read_count -= 1
        # If this is the last reader, it releases the lock that blocks writers from entering.
        if self._read_count == 0:
            # Only the final reader releases the semaphore shared with writers.
            self._wrt.release()
        # Release the counter lock so modifications to the reader count may continue.
        self._mutex.release()

    def acquire_write(self):
        # The writer acquires the semaphore to get exclusive access.
        # If readers or another writer currently hold it, the writer waits.
        self._wrt.acquire()

    def release_write(self):
        # The writer releases the semaphore after finishing its work.
        # This allows waiting readers or another writer to access the resource.
        self._wrt.release()
