import asyncio
import secrets
import threading
from datetime import datetime

import discord
from discord.ext.commands import Cog, Bot
from flask import Flask, render_template, request
import pytz
import yaml


with open('settings.yml', 'r') as f:
    settings = yaml.load(f, Loader=yaml.SafeLoader)

token = settings['Token']
RoleID = settings['RoleID']
Domain = settings['Domain']
site_key = settings['site_key']
secret_key = settings['secret_key']

client = discord.Client(intents=discord.Intents.all())
tree = discord.app_commands.CommandTree(client)
app = Flask(__name__)

# sessionの辞書宣言
session = {}


# ロールを追加
async def add_role(user, guild):
    guild = client.get_guild(guild)
    member = guild.get_member(user)
    role = guild.get_role(RoleID)
    if role:
        await member.add_roles(role)
        await member.send("認証が完了しました!")


# ボタンの処理
class VerifyView(discord.ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)


    @discord.ui.button(label="認証", style=discord.ButtonStyle.success)
    async def verify(self, inter: discord.Interaction, button: discord.ui.Button):
        global session
        # 変数を作成
        random = secrets.token_urlsafe(32)
        await inter.response.send_message(f"こちらのURLから認証を完了させてください：http://{Domain}?id={random}", ephemeral=True)

        # セッションを変数に追加
        now = datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
        user = inter.user.id
        lists = {"user": user, "server": inter.guild.id, "time": now}
        session[random] = lists
        print(session)


@client.event
async def on_ready():
    await tree.sync()
    print('ready')


# コマンドの処理
@tree.command(name='verify', description='認証メッセージを送信します')
async def verify(ctx: discord.Interaction):
    if ctx.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="認証",
            color=discord.Colour.from_rgb(0, 255, 34),
            description="認証を完了させるには下記ボタンを押してください！"
        )

        await ctx.channel.send(embed=embed, view=VerifyView())
        await ctx.response.send_message('認証メッセージを送信しました。', ephemeral=True)


# webの処理
@app.route('/', methods=["GET", "POST"])
def not_robot():
        id = request.args.get("id")
        if id is None or id == "" or not id in session:
            return render_template('index.html', id=False, msg="IDが不明です")
        else:
            return render_template('index.html', id=True, site_key=site_key, secret_key=secret_key, session=id)


# 認証成功の処理
@app.route('/complete', methods=["GET", "POST"])
def complete():
    # print(session)
    id = request.args.get("id")

    if id is None or id == "" or not id in session:
        return render_template('index.html', id=False, msg="IDが不明です")

    session_list = session[id]
    user = session_list["user"]
    guild = session_list["server"]
    asyncio.run_coroutine_threadsafe(add_role(user, guild), client.loop)

    del session[id]

    return render_template('index.html', id=False, msg="認証が完了しました")


# flaskとdiscord.pyを起動
discord_thread = threading.Thread(target=client.run, args=(token,), daemon=True)
flask_thread = threading.Thread(target=app.run, kwargs={"port": 5000}, daemon=True)
discord_thread.start()
if __name__ == "__main__":
    flask_thread.start()
