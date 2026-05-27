"""Ethereal Intelligence — Stitch export (stitch_ai_journey_curator)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EtherealTokens:
    # Core
    primary: str = "#006a61"
    on_primary: str = "#ffffff"
    primary_container: str = "#66bcb0"
    on_primary_container: str = "#004a43"
    inverse_primary: str = "#80d6c9"

    secondary: str = "#006687"
    secondary_container: str = "#88d6fd"
    on_secondary_container: str = "#005d7c"

    tertiary: str = "#604eb4"
    tertiary_container: str = "#b0a1ff"
    on_tertiary_container: str = "#422e95"
    tertiary_fixed: str = "#e6deff"

    background: str = "#f5faf9"
    on_background: str = "#171d1c"
    on_surface: str = "#171d1c"
    on_surface_variant: str = "#3e4947"
    inverse_surface: str = "#2c3131"
    inverse_on_surface: str = "#edf2f1"

    surface_container_lowest: str = "#ffffff"
    surface_container_low: str = "#f0f5f4"
    outline_variant: str = "#bdc9c6"

    # Aliases for legacy ui.py
    @property
    def surface(self) -> str:
        return self.background

    @property
    def text(self) -> str:
        return self.on_surface

    @property
    def text_muted(self) -> str:
        return self.on_surface_variant

    @property
    def primary_dark(self) -> str:
        return self.primary

    @property
    def teal(self) -> str:
        return self.primary_container


TOKENS = EtherealTokens()
