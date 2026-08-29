import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from keep_alive import keep_alive
import os

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN")


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# DATABASE
# =========================

db = sqlite3.connect("energy_box.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0
)
""")

db.commit()


def get_balance(user_id):
    cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result is None:
        cursor.execute(
            "INSERT INTO users (user_id, balance) VALUES (?, ?)",
            (user_id, 0)
        )
        db.commit()
        return 0

    return result[0]


def add_money(user_id, amount):
    get_balance(user_id)

    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id)
    )

    db.commit()


def remove_money(user_id, amount):
    get_balance(user_id)

    cursor.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
        (amount, user_id)
    )

    db.commit()


# =========================
# BOT READY
# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot đã đăng nhập: {bot.user}")


# =========================
# /BALANCE
# =========================

@bot.tree.command(
    name="balance",
    description="Xem số Energy Box của bạn"
)
async def balance(interaction: discord.Interaction):

    money = get_balance(interaction.user.id)

    embed = discord.Embed(
        title="⚡ Energy Box",
        description=(
            f"👤 **{interaction.user.display_name}**\n\n"
            f"💰 Số dư: **{money:,} Energy Box**"
        ),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)


# =========================
# /PAY
# =========================

@bot.tree.command(
    name="pay",
    description="Chuyển Energy Box cho người khác"
)
@app_commands.describe(
    user="Người nhận",
    amount="Số Energy Box muốn chuyển"
)
async def pay(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int
):

    if amount <= 0:
        await interaction.response.send_message(
            "❌ Số tiền phải lớn hơn 0!",
            ephemeral=True
        )
        return

    if user.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Bạn không thể chuyển tiền cho chính mình!",
            ephemeral=True
        )
        return

    sender_balance = get_balance(interaction.user.id)

    if sender_balance < amount:
        await interaction.response.send_message(
            f"❌ Bạn không đủ Energy Box!\n"
            f"💰 Bạn đang có: **{sender_balance:,}**",
            ephemeral=True
        )
        return

    remove_money(interaction.user.id, amount)
    add_money(user.id, amount)

    await interaction.response.send_message(
        f"⚡ **{interaction.user.display_name}** đã chuyển "
        f"**{amount:,} Energy Box** cho **{user.display_name}**!"
    )


# =========================
# /GIVE
# ADMIN ONLY
# =========================

@bot.tree.command(
    name="give",
    description="Cấp Energy Box cho người chơi"
)
@app_commands.describe(
    user="Người nhận",
    amount="Số tiền"
)
@app_commands.checks.has_permissions(administrator=True)
async def give(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int
):

    if amount <= 0:
        await interaction.response.send_message(
            "❌ Số tiền phải lớn hơn 0!",
            ephemeral=True
        )
        return

    add_money(user.id, amount)

    new_balance = get_balance(user.id)

    await interaction.response.send_message(
        f"✅ Đã cấp **{amount:,} Energy Box** cho {user.mention}\n"
        f"💰 Số dư mới: **{new_balance:,}**"
    )


# =========================
# /REMOVE
# ADMIN ONLY
# =========================

@bot.tree.command(
    name="remove",
    description="Trừ Energy Box của người chơi"
)
@app_commands.describe(
    user="Người bị trừ tiền",
    amount="Số tiền"
)
@app_commands.checks.has_permissions(administrator=True)
async def remove(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int
):

    if amount <= 0:
        await interaction.response.send_message(
            "❌ Số tiền phải lớn hơn 0!",
            ephemeral=True
        )
        return

    balance = get_balance(user.id)

    if balance < amount:
        await interaction.response.send_message(
            "❌ Người chơi không đủ tiền!",
            ephemeral=True
        )
        return

    remove_money(user.id, amount)

    new_balance = get_balance(user.id)

    await interaction.response.send_message(
        f"✅ Đã trừ **{amount:,} Energy Box** của {user.mention}\n"
        f"💰 Số dư mới: **{new_balance:,}**"
    )


# =========================
# ERROR HANDLER
# =========================

@give.error
@remove.error
async def admin_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "❌ Bạn không có quyền sử dụng lệnh này!",
            ephemeral=True
        )


# =========================
# START BOT
# =========================
keep_alive()

bot.run(TOKEN)
