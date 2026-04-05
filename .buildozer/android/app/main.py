from kivy.app import App
from kivy.uix.label import Label

class AssistenteApp(App):
    def build(self):
        return Label(text="FUNCIONANDO 😄🔥")

if __name__ == "__main__":
    AssistenteApp().run()