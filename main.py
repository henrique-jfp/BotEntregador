#!/usr/bin/env python3
"""Ponto de entrada limpo do Bot Entregador (substitui main.py legado).

Use: python bootstrap.py
"""
from bot.application import run_bot
from bot.server import start_health_server
from bot.utils.singleton import ensure_single_instance, clear_lock
from bot.config import logger


def main() -> None:
    start_health_server()
    if not ensure_single_instance():
        logger.warning('Outra instância ativa; encerrando bootstrap.')
        return
    run_bot()


if __name__ == '__main__':  # pragma: no cover
    try:
        main()
    finally:
        clear_lock()

# Fim.