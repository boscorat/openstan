import os


class Paths:
    base: str = os.path.dirname(__file__)
    icons: str = os.path.join(base, "icons")
    data: str = os.path.join(base, "data")

    # File loaders.
    @classmethod
    def icon(cls, filename) -> str:
        return os.path.join(cls.icons, filename)

    @classmethod
    def databases(cls, filename) -> str:
        return os.path.join(cls.data, filename)
