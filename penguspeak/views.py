"""Panel de configuración y navegador de voces de PenguSpeak."""
import os
import discord
from penguspeak.database import (
    get_nickname, get_user_voice_preference, remove_nickname,
    reset_user_preferences, set_nickname, set_unified_voice,
)
from penguspeak.text import is_valid_nickname, normalize_spaces
from penguspeak.voices import EDGE_VOICES, get_gender_voices, get_voice_label

DEMOS_PER_PAGE = 5


def config_embed(user_id):
    voice_id = get_user_voice_preference(user_id, 'edge')
    if voice_id not in EDGE_VOICES:
        voice_id = 'edge_jorge'
    nickname = get_nickname(user_id)
    embed = discord.Embed(
        title='🐧 PenguSpeak · Configuración',
        description='Personaliza cómo PenguSpeak lee tus mensajes.',
        color=discord.Color.blurple(),
    )
    embed.add_field(name='🔊 Tu voz', value=get_voice_label(voice_id), inline=False)
    embed.add_field(name='🏷️ Tu apodo', value=nickname or 'Sin apodo personalizado', inline=False)
    embed.set_footer(text='Solo tú puedes utilizar este panel.')
    return embed


class OwnedView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=300)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('Este panel pertenece a otro usuario.', ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True


class NicknameModal(discord.ui.Modal, title='Editar apodo de PenguSpeak'):
    nickname = discord.ui.TextInput(label='Apodo', placeholder='Cómo quieres que te llamemos', max_length=30)

    def __init__(self, owner_id):
        super().__init__()
        self.owner_id = owner_id
        current = get_nickname(owner_id)
        if current:
            self.nickname.default = current

    async def on_submit(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('Este formulario pertenece a otro usuario.', ephemeral=True)
            return
        value = normalize_spaces(str(self.nickname.value))
        if not value or not is_valid_nickname(value):
            await interaction.response.send_message('❌ El apodo debe contener solo letras, números y espacios.', ephemeral=True)
            return
        set_nickname(self.owner_id, value)
        await interaction.response.send_message(f'✅ Apodo actualizado: **{value}**. Abre de nuevo el panel para ver el cambio.', ephemeral=True)


class VoiceSelector(discord.ui.Select):
    def __init__(self, gender, owner_id):
        self.gender = gender
        self.owner_id = owner_id
        options = [discord.SelectOption(label=data['name'], value=voice_id, description=data['country'], emoji=data['flag']) for voice_id, data in get_gender_voices(gender)]
        super().__init__(placeholder='Selecciona tu voz', min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('Este selector pertenece a otro usuario.', ephemeral=True)
            return
        voice_id = self.values[0]
        set_unified_voice(interaction.user.id, voice_id)
        await interaction.response.send_message(f'✅ Voz seleccionada: **{get_voice_label(voice_id)}**. Se utilizará en ambos servicios.', ephemeral=True)


class VoiceBrowserView(OwnedView):
    def __init__(self, gender, owner_id):
        super().__init__(owner_id)
        self.gender = gender
        self.page = 0
        self.voices = get_gender_voices(gender)
        self.pages = [self.voices[i:i + DEMOS_PER_PAGE] for i in range(0, len(self.voices), DEMOS_PER_PAGE)]
        self.add_item(VoiceSelector(gender, owner_id))
        self.update_buttons()

    def get_page_content(self):
        title = '👨 Voces masculinas' if self.gender == 'male' else '👩 Voces femeninas'
        lines = [f'### {title}', f'Página **{self.page + 1}/{len(self.pages)}**', '']
        for _, data in self.pages[self.page]:
            lines.append(f"{data['flag']} **{data['name']}** · {data['country']}")
        lines.extend(['', 'Selecciona una voz en el menú. Los MP3 adjuntos son sus demostraciones.'])
        return '\n'.join(lines)

    def get_page_files(self):
        files = []
        for _, data in self.pages[self.page]:
            demo = data.get('demo')
            if demo and os.path.isfile(demo):
                files.append(discord.File(demo, filename=os.path.basename(demo)))
        return files

    def update_buttons(self):
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= len(self.pages) - 1

    @discord.ui.button(label='Anterior', emoji='◀️', style=discord.ButtonStyle.secondary, row=1)
    async def previous_button(self, interaction, button):
        self.page = max(0, self.page - 1)
        self.update_buttons()
        await interaction.response.edit_message(content=self.get_page_content(), attachments=self.get_page_files(), view=self)

    @discord.ui.button(label='Siguiente', emoji='▶️', style=discord.ButtonStyle.secondary, row=1)
    async def next_button(self, interaction, button):
        self.page = min(len(self.pages) - 1, self.page + 1)
        self.update_buttons()
        await interaction.response.edit_message(content=self.get_page_content(), attachments=self.get_page_files(), view=self)

    @discord.ui.button(label='Volver al panel', emoji='⚙️', style=discord.ButtonStyle.primary, row=1)
    async def back_button(self, interaction, button):
        await interaction.response.edit_message(content=None, attachments=[], embed=config_embed(self.owner_id), view=ConfigView(self.owner_id))


class ResetConfirmView(OwnedView):
    @discord.ui.button(label='Solo restablecer voz', style=discord.ButtonStyle.secondary)
    async def reset_voice(self, interaction, button):
        reset_user_preferences(self.owner_id, remove_alias=False)
        await interaction.response.edit_message(content='✅ Voz restablecida.', embed=config_embed(self.owner_id), view=ConfigView(self.owner_id))

    @discord.ui.button(label='Restablecer todo', style=discord.ButtonStyle.danger)
    async def reset_all(self, interaction, button):
        reset_user_preferences(self.owner_id, remove_alias=True)
        await interaction.response.edit_message(content='✅ Voz y apodo restablecidos.', embed=config_embed(self.owner_id), view=ConfigView(self.owner_id))

    @discord.ui.button(label='Cancelar', style=discord.ButtonStyle.primary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(content=None, embed=config_embed(self.owner_id), view=ConfigView(self.owner_id))


class ConfigView(OwnedView):
    @discord.ui.button(label='Voces masculinas', emoji='🎙️', style=discord.ButtonStyle.primary, row=0)
    async def male(self, interaction, button):
        view = VoiceBrowserView('male', self.owner_id)
        await interaction.response.edit_message(content=view.get_page_content(), embed=None, attachments=view.get_page_files(), view=view)

    @discord.ui.button(label='Voces femeninas', emoji='🎙️', style=discord.ButtonStyle.primary, row=0)
    async def female(self, interaction, button):
        view = VoiceBrowserView('female', self.owner_id)
        await interaction.response.edit_message(content=view.get_page_content(), embed=None, attachments=view.get_page_files(), view=view)

    @discord.ui.button(label='Editar apodo', emoji='✏️', style=discord.ButtonStyle.secondary, row=1)
    async def edit_nickname(self, interaction, button):
        await interaction.response.send_modal(NicknameModal(self.owner_id))

    @discord.ui.button(label='Quitar apodo', emoji='🗑️', style=discord.ButtonStyle.secondary, row=1)
    async def clear_nickname(self, interaction, button):
        if not get_nickname(self.owner_id):
            await interaction.response.send_message('No tienes un apodo personalizado.', ephemeral=True)
            return
        remove_nickname(self.owner_id)
        await interaction.response.edit_message(embed=config_embed(self.owner_id), view=ConfigView(self.owner_id))

    @discord.ui.button(label='Restablecer', emoji='🔄', style=discord.ButtonStyle.danger, row=2)
    async def reset(self, interaction, button):
        await interaction.response.edit_message(content='¿Qué deseas restablecer?', embed=None, view=ResetConfirmView(self.owner_id))

    @discord.ui.button(label='Actualizar', emoji='🔃', style=discord.ButtonStyle.secondary, row=2)
    async def refresh(self, interaction, button):
        await interaction.response.edit_message(content=None, embed=config_embed(self.owner_id), view=ConfigView(self.owner_id))
