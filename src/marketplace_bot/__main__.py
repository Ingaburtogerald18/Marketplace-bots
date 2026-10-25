"""Arranque.

    python -m marketplace_bot            -> abre la ventana
    python -m marketplace_bot motor ...  -> corre el bot sin ventana (lo usa la ventana)
"""
import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "motor":
        from .motor.cli import main as motor

        sys.exit(motor(sys.argv[2:]))
    from .ui.app import main as ventana

    ventana()


if __name__ == "__main__":
    main()
