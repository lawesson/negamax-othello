from ui.api import create_gui


def main():
    with create_gui() as gui:
        gui.init()
        gui.run()


if __name__ == '__main__':
    main()
