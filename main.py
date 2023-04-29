import secrets
import threading

import discord
from discord.ext.commands import Cog, Bot
from flask import Flask, render_template, request
import yaml


with open('settings.yml', 'r') as f:
    settings = yaml.load(f, Loader=yaml.SafeLoader)

token = settings['Token']
RoleID = settings['RoleID']
Domain = settings['Domain']
role_id = settings['role_id']
site_key = settings['site_key']
secret_key = settings['secret_key']

client = discord.Client(intents=discord.Intents.all())
tree = discord.app_commands.CommandTree(client)
app = Flask(__name__)

session = {}


async def add_role(user, guild):
    guild = client.get_guild(guild)
    member = guild.get_member(user)
    role = discord.utils.get(guild.roles, id=role_id)
    if role:
        await member.add_roles(role)


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
        user = inter.user.id
        lists = [user, inter.guild.id]
        session[random] = lists
        print(session)


@client.event
async def on_ready():
    await tree.sync()
    print('ready')


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


@app.route('/', methods=["GET", "POST"])
async def not_robot():
    global session
    print(session)
    if request.method == "GET":
        id = request.args.get("id")
        if id is None or id == "":
            return render_template('index.html', id=False)
        else:
            return render_template('index.html', id=True, site_key=site_key, secret_key=secret_key)
    else:
        id = request.args.get("id")

        session_list = session[id]
        user = session_list[0]
        guild = session_list[1]
        guild = client.get_guild(guild)
        member = guild.get_member(user)
        role = discord.utils.get(guild.roles, id=role_id)
        if role:
            await member.add_roles(role)
        return render_template('index.html', id='success')


# flaskとdiscord.pyを起動
discord_thread = threading.Thread(target=client.run, args=(token,), daemon=True)
flask_thread = threading.Thread(target=app.run, kwargs={"port": 5000}, daemon=True)
discord_thread.start()
if __name__ == "__main__":
    flask_thread.start()
