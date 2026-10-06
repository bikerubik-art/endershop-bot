import discord
from discord.ext import commands
import random

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

USER_LIMITS = {}

# =====================================================================
# 📌 TUTAJ WKLEJAJ SWOJE LINKI DO GRAFIK (ZAMIAST TEGO TEKSTU W CUDZYSLOWIE):
# =====================================================================
PANEL_IMAGE_URL = "https://cdn.phototourl.com/member/2026-10-06-88e72749-c7fd-4488-a4b1-efa9ad0967a0.png"
VERIFY_IMAGE_URL = "https://cdn.phototourl.com/member/2026-10-06-88e72749-c7fd-4488-a4b1-efa9ad0967a0.png"


# ==========================================
# 1. WERYFIKACIJA MATEMATYCZNA
# ==========================================
class MathCaptchaModal(discord.ui.Modal, title="Weryfikacja Matematyczna"):
    def __init__(self, correct_answer: int, role_name: str):
        super().__init__()
        self.correct_answer = correct_answer
        self.role_name = role_name

        self.answer_input = discord.ui.TextInput(
            label="Wpisz wynik poniższego działania:",
            placeholder="Wpisz samą cyfrę...",
            required=True,
            max_length=5
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_answer = int(self.answer_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ To nie jest poprawna liczba!", ephemeral=True)
            return

        if user_answer == self.correct_answer:
            role = discord.utils.get(interaction.guild.roles, name=self.role_name)
            if not role:
                await interaction.response.send_message(f"⚠️ Rola **{self.role_name}** nie została jeszcze utworzona! Użyj komendy !dodajrolezwerf", ephemeral=True)
                return
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("✅ **Zweryfikowano pomyślnie!** Otrzymałeś dostęp do serwera.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Bot nie ma uprawnień do nadania roli (przesuń rolę bota wyżej!).", ephemeral=True)
        else:
            await interaction.response.send_message("❌ **Błędny wynik!** Spróbuj ponownie.", ephemeral=True)

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify_btn")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        operator = random.choice(["+", "-"])

        if operator == "+":
            answer = num1 + num2
            q_text = f"{num1} + {num2}"
        else:
            if num1 < num2:
                num1, num2 = num2, num1
            answer = num1 - num2
            q_text = f"{num1} - {num2}"

        modal = MathCaptchaModal(correct_answer=answer, role_name="Zweryfikowany")
        modal.title = f"Weryfikacja: Ile to {q_text}?"
        await interaction.response.send_modal(modal)

# ==========================================
# 2. MODALE DLA KAŻDEJ OPCJI TICKETA
# ==========================================

class OrderModal(discord.ui.Modal, title="Formularz Zamówienia"):
    def __init__(self):
        super().__init__()
        self.payment = discord.ui.TextInput(label="Forma płatności", placeholder="np. blik, przelew...", required=True, max_length=50)
        self.amount = discord.ui.TextInput(label="Kwota (PLN)", placeholder="np. 45, 120, 250...", required=True, max_length=10)
        self.add_item(self.payment)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            kwota = float(self.amount.value.strip().replace(",", "."))
        except ValueError:
            await interaction.response.send_message("❌ Podana kwota musi być liczbą!", ephemeral=True)
            return

        if 1 <= kwota <= 50:
            kategoria_tag = "1-50"
            color = 0x5865F2
        elif 50.01 <= kwota <= 150:
            kategoria_tag = "50-150"
            color = 0xFEE75C
        else:
            kategoria_tag = "200+"
            color = 0xED4245

        guild = interaction.guild
        member = interaction.user
        czysta_platnosc = self.payment.value.lower().strip().replace(" ", "-")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        for user_id, limit in USER_LIMITS.items():
            staff = guild.get_member(user_id)
            if staff:
                if kwota > limit:
                    overwrites[staff] = discord.PermissionOverwrite(view_channel=False)
                else:
                    overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)

        channel_name = f"💲-{int(kwota)}-{czysta_platnosc}"
        channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
        await interaction.response.send_message(f"✅ Utworzono ticket: {channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"🛒 ⠂ZAMÓWIENIE ({kategoria_tag} PLN)",
            description=f"Witaj {member.mention}!\n\n💳 **Płatność:** {self.payment.value}\n💵 **Kwota:** {kwota} PLN\n\n*Administracja wkrótce odpowie.*",
            color=color
        )
        embed.set_image(url=PANEL_IMAGE_URL)
        embed.set_footer(text="ENDER SHOP • Zamówienia")
        await channel.send(embed=embed, view=TicketInsideView())

class ComplaintModal(discord.ui.Modal, title="Formularz Reklamacji"):
    def __init__(self):
        super().__init__()
        self.reason = discord.ui.TextInput(label="Opis problemu / Reklamacji", style=discord.TextStyle.paragraph, placeholder="Opisz dokładnie, co się stało...", required=True, max_length=500)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await create_standard_ticket(interaction, "REKLAMACJA", self.reason.value, 0xED4245)

class ApplyModal(discord.ui.Modal, title="Formularz Rekrutacyjny"):
    def __init__(self):
        super().__init__()
        self.experience = discord.ui.TextInput(label="Doświadczenie / Budżet / Wiek", style=discord.TextStyle.paragraph, placeholder="Napisz coś o sobie...", required=True, max_length=500)
        self.add_item(self.experience)

    async def on_submit(self, interaction: discord.Interaction):
        await create_standard_ticket(interaction, "REKRUTACJA", self.experience.value, 0x57F287)

class HelpModal(discord.ui.Modal, title="Potrzebuję Pomocy"):
    def __init__(self):
        super().__init__()
        self.details = discord.ui.TextInput(label="W czym możemy Ci pomóc?", style=discord.TextStyle.paragraph, placeholder="Opisz swoje pytanie...", required=True, max_length=500)
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        await create_standard_ticket(interaction, "POMOC", self.details.value, 0x5865F2)

class ScammerModal(discord.ui.Modal, title="Zgłoszenie Oszusta"):
    def __init__(self):
        super().__init__()
        self.evidence = discord.ui.TextInput(label="Nick oszusta i dowody / opis", style=discord.TextStyle.paragraph, placeholder="Podaj dane i opisz sytuację...", required=True, max_length=500)
        self.add_item(self.evidence)

    async def on_submit(self, interaction: discord.Interaction):
        await create_standard_ticket(interaction, "ZGLOSZENIE-SCAMA", self.evidence.value, 0xED4245)

async def create_standard_ticket(interaction, title_prefix, content, color):
    guild = interaction.guild
    member = interaction.user
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }

    for user_id, limit in USER_LIMITS.items():
        staff = guild.get_member(user_id)
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)

    safe_name = member.name.lower().replace(" ", "-")
    channel = await guild.create_text_channel(name=f"ticket-{safe_name}", overwrites=overwrites)
    await interaction.response.send_message(f"✅ Utworzono ticket: {channel.mention}", ephemeral=True)

    embed = discord.Embed(
        title=f"📂 ⠂{title_prefix}",
        description=f"Witaj {member.mention}!\n\n**Treść zgłoszenia:**\n{content}\n\n*Administracja wkrótce odpowie.*",
        color=color
    )
    embed.set_image(url=PANEL_IMAGE_URL)
    embed.set_footer(text="ENDER SHOP • System Ticketów")
    await channel.send(embed=embed, view=TicketInsideView())

# ==========================================
# 3. WIDOK WEWNĄTRZ TICKETA
# ==========================================
class TicketInsideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zajmij ticket", style=discord.ButtonStyle.primary, emoji="🙋‍♂️", custom_id="claim_tkt")
    async def claim_tkt(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Brak uprawnień do przejęcia ticketa!", ephemeral=True)
            return
        await interaction.response.send_message(f"🔒 Ticket przejęty przez: **{interaction.user.mention}**", ephemeral=False)
        button.disabled = True
        button.label = f"Przejęto przez {interaction.user.name}"
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_tkt")
    async def close_tkt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⚠️ Zamykanie kanału za 3 sekundy...", ephemeral=True)
        import asyncio
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete()
        except:
            pass

# ==========================================
# 4. MENU ROZWIJANE TICKETÓW
# ==========================================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Chcę złożyć zamówienie", description="Podaj formę płatności i kwotę.", emoji="🛒"),
            discord.SelectOption(label="Chcę złożyć reklamację", description="Zgłoś problem z produktem lub usługą.", emoji="❕"),
            discord.SelectOption(label="Chcę aplikować", description="Wyślij zgłoszenie rekrutacyjne i budżet.", emoji="👤"),
            discord.SelectOption(label="Potrzebuję pomocy", description="Zadaj pytanie lub opisz problem.", emoji="🔍"),
            discord.SelectOption(label="Chcę zgłosić oszusta", description="Zgłoś podejrzaną osobę i dowody.", emoji="❕")
        ]
        super().__init__(placeholder="📂 ⠂Wybierz kategorię zgłoszenia!", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        wybrana = self.values[0]
        if "zamówienie" in wybrana.lower():
            await interaction.response.send_modal(OrderModal())
        elif "reklamację" in wybrana.lower():
            await interaction.response.send_modal(ComplaintModal())
        elif "aplikować" in wybrana.lower():
            await interaction.response.send_modal(ApplyModal())
        elif "pomocy" in wybrana.lower():
            await interaction.response.send_modal(HelpModal())
        elif "oszusta" in wybrana.lower():
            await interaction.response.send_modal(ScammerModal())

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ==========================================
# 5. KOMENDY BOTA
# ==========================================
@bot.event
async def on_ready():
    print(f'Zalogowano jako: {bot.user.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

    embed = discord.Embed(
        title="🏢 ⠂E N D E R   S H O P ™  ×  T I C K E T Y",
        description=(
            "📄 ⠂**Chcesz** złożyć zamówienie, uzyskać pomoc, zgłosić reklamację, zgłosić oszusta albo aplikować do zespołu?\n\n"
            "🔔 ⠂Wybierz odpowiednią kategorię z listy poniżej, a pojawi się formularz do wypełnienia."
        ),
        color=0x5865F2
    )
    embed.set_image(url=PANEL_IMAGE_URL)
    embed.set_footer(text="© ENDER SHOP", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    await ctx.send(embed=embed, view=TicketView())

@bot.command()
@commands.has_permissions(administrator=True)
async def weryfikacja(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

    embed = discord.Embed(
        title="🔒 ⠂W E R Y F I K A C J A   S E R W E RA",
        description=(
            "Aby uzyskać pełny dostęp do serwera **ENDER SHOP**, przejdź weryfikację matematyczną.\n\n"
            "👉 Kliknij przycisk poniżej i rozwiąż równanie!"
        ),
        color=0x57F287
    )
    embed.set_image(url=VERIFY_IMAGE_URL)
    embed.set_footer(text="© ENDER SHOP • Bezpieczeństwo", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    await ctx.send(embed=embed, view=VerificationView())

@bot.command()
@commands.has_permissions(administrator=True)
async def dodajrolezwerf(ctx):
    guild = ctx.guild
    existing_role = discord.utils.get(guild.roles, name="Zweryfikowany")
    if existing_role:
        await ctx.send("ℹ️ Rola **Zweryfikowany** już istnieje na tym serwerze.")
    else:
        await guild.create_role(name="Zweryfikowany", color=discord.Color.green(), reason="Tworzenie roli weryfikacji przez bota")
        await ctx.send("✅ Pomyślnie utworzono rolę **Zweryfikowany**!")

@bot.command()
@commands.has_permissions(administrator=True)
async def dodaj_limit(ctx, member: discord.Member, kwota: float):
    """Komenda: !dodaj_limit @Użytkownik 50"""
    USER_LIMITS[member.id] = kwota
    
    nowy_nick = f"[Limit {int(kwota)}] {member.name}"
    
    try:
        await member.edit(nick=nowy_nick)
        await ctx.send(f"✅ Ustawiono limit **{kwota} PLN** dla {member.mention}, zmieniono nick na `{nowy_nick}` oraz nadano uprawnienia do zarządzania ticketami.")
    except discord.Forbidden:
        await ctx.send(f"⚠️ Zapisano limit {kwota} PLN, ale bot **ne ma uprawnień do zmiany nicku** tego użytkownika (przesuń rolę bota wyżej w ustawieniach serwera!).")

import os
# Bot pobierze token z bezpiecznej zmiennej środowiskowej
bot.run(os.getenv("DISCORD_TOKEN"))