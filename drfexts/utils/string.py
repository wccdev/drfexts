class ColorString(str):
    def __new__(cls, string, color=None):
        instance = super().__new__(cls, string)
        instance.color = color
        return instance
