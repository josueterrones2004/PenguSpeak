import os

import discord

from penguspeak.database import set_user_voice
from penguspeak.voices import (
    get_gender_voices,
    get_voice_label,
)


DEMOS_PER_PAGE = 5


class VoiceSelector(discord.ui.Select):
    def __init__(
        self,
        gender,
        owner_id,
    ):
        self.gender = gender
        self.owner_id = owner_id

        options = []

        for voice_id, data in get_gender_voices(
            gender
        ):
            description = (
                f'{data["country"]} · Edge TTS'
            )

            options.append(
                discord.SelectOption(
                    label=data["name"],
                    value=voice_id,
                    description=description,
                    emoji=data["flag"],
                )
            )

        super().__init__(
            placeholder="Selecciona una voz",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Este selector pertenece a otro usuario.",
                ephemeral=True,
            )
            return

        voice_id = self.values[0]

        set_user_voice(
            interaction.user.id,
            voice_id,
        )

        await interaction.response.send_message(
            f"✅ Voz seleccionada: "
            f"**{get_voice_label(voice_id)}**",
            ephemeral=True,
        )


class VoiceBrowserView(discord.ui.View):
    def __init__(
        self,
        gender,
        owner_id,
    ):
        super().__init__(
            timeout=300
        )

        self.gender = gender
        self.owner_id = owner_id
        self.page = 0

        self.voices = get_gender_voices(
            gender
        )

        self.pages = [
            self.voices[
                i:i + DEMOS_PER_PAGE
            ]
            for i in range(
                0,
                len(self.voices),
                DEMOS_PER_PAGE,
            )
        ]

        self.add_item(
            VoiceSelector(
                gender=gender,
                owner_id=owner_id,
            )
        )

        self.update_buttons()

    def get_page_content(self):
        if self.gender == "male":
            title = "👨 Voces masculinas"
        else:
            title = "👩 Voces femeninas"

        total_pages = len(
            self.pages
        )

        lines = [
            f"### {title}",
            "",
            (
                f"Página "
                f"**{self.page + 1}/{total_pages}**"
            ),
            "",
        ]

        for voice_id, data in self.pages[
            self.page
        ]:
            lines.append(
                f'{data["flag"]} '
                f'**{data["name"]}** '
                f'· {data["country"]}'
            )

        lines.extend(
            [
                "",
                (
                    "Usa el selector de abajo "
                    "para elegir tu voz."
                ),
            ]
        )

        return "\n".join(
            lines
        )

    def get_page_files(self):
        files = []

        for voice_id, data in self.pages[
            self.page
        ]:
            demo_path = data.get(
                "demo"
            )

            if (
                demo_path
                and os.path.exists(
                    demo_path
                )
            ):
                files.append(
                    discord.File(
                        demo_path,
                        filename=os.path.basename(
                            demo_path
                        ),
                    )
                )

        return files

    def update_buttons(self):
        self.previous_button.disabled = (
            self.page <= 0
        )

        self.next_button.disabled = (
            self.page
            >= len(self.pages) - 1
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Este menú pertenece a otro usuario.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="Anterior",
        style=discord.ButtonStyle.secondary,
        emoji="◀️",
    )
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.page > 0:
            self.page -= 1

        self.update_buttons()

        await interaction.response.edit_message(
            content=self.get_page_content(),
            attachments=self.get_page_files(),
            view=self,
        )

    @discord.ui.button(
        label="Siguiente",
        style=discord.ButtonStyle.secondary,
        emoji="▶️",
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if (
            self.page
            < len(self.pages) - 1
        ):
            self.page += 1

        self.update_buttons()

        await interaction.response.edit_message(
            content=self.get_page_content(),
            attachments=self.get_page_files(),
            view=self,
        )
