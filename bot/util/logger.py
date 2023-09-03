from logging import INFO, FileHandler, Formatter, getLogger


def create_logger(file_name: str, log_name: str, log_level = INFO):
    formatter = Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s", 
        datefmt='%d.%m.%Y %H:%M:%S')

    handler = FileHandler(file_name)
    handler.setFormatter(formatter)

    logger = getLogger(log_name)
    logger.setLevel(log_level)

    logger.addHandler(handler)

    return logger
