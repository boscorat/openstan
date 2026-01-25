import os


class Paths:
    base = os.path.dirname(__file__)
    icons = os.path.join(base, "icons")
    data = os.path.join(base, "data")

    # File loaders.
    @classmethod
    def icon(cls, filename):
        return os.path.join(cls.icons, filename)

    @classmethod
    def databases(cls, filename):
        return os.path.join(cls.data, filename)
