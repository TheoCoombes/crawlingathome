class ServerError(Exception):
    pass

class ZeroJobError(Exception):
    pass

class DumpError(Exception):
    pass

class InvalidURLError(Exception):
    pass

class WorkerTimedOutError(Exception):
    pass
