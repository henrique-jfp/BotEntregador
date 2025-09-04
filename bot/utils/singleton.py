import os, errno
from pathlib import Path
from bot.config import logger

LOCK_FILE = '/tmp/bot_entregador.lock'

def ensure_single_instance() -> bool:
    try:
        tmpdir = Path('/tmp')
        if not tmpdir.exists():
            return True
        lock_path = Path(LOCK_FILE)
        if lock_path.exists():
            try:
                with open(lock_path, 'r') as f:
                    old_pid = int(f.read().strip())
                try:
                    os.kill(old_pid, 0)
                    logger.warning(f'Outra instância ativa PID {old_pid}.')
                    return False
                except ProcessLookupError:
                    logger.info('Lock órfão. Removendo...')
                    lock_path.unlink()
            except Exception:
                lock_path.unlink(missing_ok=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, 'w') as f:
            f.write(str(os.getpid()))
        logger.info('Lock adquirido.')
        return True
    except OSError as e:
        if e.errno == errno.EEXIST:
            logger.warning('Instância concorrente detectada.')
            return False
        logger.error(f'Falha lock: {e}')
        return True

def clear_lock():
    try:
        Path(LOCK_FILE).unlink(missing_ok=True)
    except Exception:
        pass