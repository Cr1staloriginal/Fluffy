# utils/colors.py
import disnake

COLOR_MAIN = 0xb3d1f3   # нежно-голубой
COLOR_ACCENT = 0xfff7d5 # кремовый

def main_color():
    return disnake.Color(COLOR_MAIN)

def accent_color():
    return disnake.Color(COLOR_ACCENT)