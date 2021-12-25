import discord
import os
import json
import pathlib
import time
from datetime import date, datetime
from discord.ext import commands
import datetime

bot = commands.Bot(command_prefix='!', owner_id=384331331527639042)
bot.owner_id = 384331331527639042

class UnbanLogger:
    def __init__(self, guild: discord.Guild):
        self.startTime = time.time()
        self.unbannedUsers = {}
        self.reInvitedUsers = []
        self.server = guild
        self.log = ''

    def logPass(self, user: discord.User, banner: discord.User, userUnbanned: bool, userReinvited: bool):
        if userUnbanned:
            self.unbannedUsers.update({f'{user.name}#{user.discriminator}': f'{banner.name}#{banner.discriminator}'})
        if userReinvited:
            self.reInvitedUsers.append(f'{user.name}#{user.discriminator}')
        return

    def formatLog(self):
        self.reInvitedUsers.sort()
        self.log = f"Succesfully managed to unban {len(self.unbannedUsers)} from the server {self.server.name} in {time.time() - self.startTime} seconds.\n{len(self.reInvitedUsers)} of the unbanned users were successfully DM'd with an invite link to the server.\nBelow, is more detailed information about who was unbanned, as well as whether or not a re-invite was sent.\n\n\n\n\n"
        for unbannedUser in self.unbannedUsers.keys():
            if unbannedUser in self.reInvitedUsers:
                self.log = f'{self.log}{unbannedUser} was unbanned and re-invited. User was originally banned by {self.unbannedUsers[unbannedUser]}\n'
            else:
                self.log = f'{self.log}{unbannedUser} was unbanned however a re-invite could not be sent. User was originally banned by {self.unbannedUsers[unbannedUser]}\n'
        print(self.log)
        return

    def writeLog(self):
        self.formatLog()
        server = self.server
        logPath = pathlib.Path(f'./logs/{server.name}-{server.id}__log__{datetime.now().strftime("%d-%m-%Y_%H-%M_%Z")}.txt')
        with open(logPath, 'wt') as writeLog:
            writeLog.write(self.log)
        return logPath

def isOwner():
    async def predicate(ctx):
        return ctx.author.id == ctx.guild.owner_id
    return commands.check(predicate)

def isMod():
    async def predicate(ctx):
        with open(pathlib.Path(f'./guilds/{ctx.guild.id}.json'), 'rt') as guildConfigFile:
            guildData = json.loads(guildConfigFile.read())
        return ctx.author.id in guildData['modList']
    return commands.check(predicate)

def readConfig(guild: discord.Guild):
    with open(f'guilds/{guild.id}.json', 'rt') as readConfig:
        guildConfig = json.loads(readConfig.read())
    return guildConfig

async def checkModBans(guild: discord.Guild) -> list:
    modBans = []
    guildConfig = readConfig(guild)
    auditLog = await guild.audit_logs(limit=None, action=discord.AuditLogAction.ban).flatten()
    for entry in auditLog:
        target = entry.target
        if entry.user.id in guildConfig['modList']:
            modBans.append(target.id)
        else:
            continue
    return modBans

# Finds wrongully banned users using dyno ban logs
async def findbannedUsersViaDyno(guild, channelId, startDateTime: datetime.datetime, endDateTime: datetime.datetime, limit=None) -> list:
    channel = bot.get_channel(channelId)
    modBans = await checkModBans(guild)
    bannedUsers = []
    messages = await channel.history(after=startDateTime, before=endDateTime, limit=limit, oldest_first=True).flatten()
    for message in messages:
        if message.author.name == 'Dyno':
            try:
                embed = message.embeds[0].to_dict
            except:
                continue
            if embed['author']['name'] == 'Member Banned':
                target = int(embed['footer']['text'].lstrip('ID: '))
                if int(target) not in modBans:
                    bannedUsers.append(message)
                else:
                    continue
            else:
                continue
        else:
            continue
    return bannedUsers

@bot.event
async def on_ready():
    print('Bot has connected')
    configDir = pathlib.Path('./guilds/')
    for guild in bot.guilds:
        guildConfigPath = pathlib.Path(f'{configDir}/{guild.id}.json')
        if guildConfigPath.exists():
            continue
        else:
            with open(guildConfigPath, 'wt') as initConfig:
                initConfig.write(json.dumps({}))

@bot.command(name='repair', aliases=['cleanup'])
@isMod()
async def repair(ctx):
    guild = ctx.guild
    failCount = 0
    banFails = 0
    with open(f'guilds/{guild.id}.json', 'rt') as readConfig:
        guildConfig = json.loads(readConfig.read())
    logger = UnbanLogger(guild)
    invite = await guild.get_channel(guildConfig['channelId']).create_invite(reason='Apocalypse Repair Invite')
    auditLog = await guild.audit_logs(limit=None, action=discord.AuditLogAction.ban).flatten()
    for entry in auditLog:
        user = entry.target
        unbanned = False
        reInvited = False
        print(user)

        if ((entry.user.id not in guildConfig['modList']) or (user not in [892118738537697400, 892118734695702548])):
            try:
                await guild.unban(user)
                unbanned = True
            except:
                banFails += 1
                continue
            if unbanned:
                try:
                    await user.send(content=f'It appears that you were wrongfully banned in the server "{guild.name}" You have been unbanned, and can rejoin using this link:\n{invite.url}')
                    reInvited = True
                except:
                    print(f'Failed to send invite to {user.name}, passing.')
                    failCount += 1
            logger.logPass(user, entry.user, unbanned, reInvited)
        else:
            continue
    logFile = discord.File(logger.writeLog())
    await ctx.author.send(content=f'Finished unbanning {len(auditLog) - banFails} out of {len(auditLog)} banned user(s) from the server {guild.name}.\nFailed to message {failCount} user(s) with a new invite.\nA full log of the run has been attached to this message.', file=logFile)
    return

@bot.command(name='dynoRepair')
@isMod()
async def dynoRepair(ctx):
    guild = ctx.guild
    guildConfig = readConfig(guild)
    channel = ctx.message.channel_mentions[0]
    print(channel)
    time.sleep(10)
    #if(input('continue? ') != 'y'):
        #print('Aborting')
        #return
    banFails = 0
    failCount = 0
    limit = None
    start = datetime.datetime(2021, 9, 27, 17)
    end = datetime.datetime(2021, 9, 27, 20, 2)
    logger = UnbanLogger(guild)
    invite = await guild.get_channel(guildConfig['channelId']).create_invite(reason='Apocalypse Repair Invite')
    bannedUsers = await findbannedUsersViaDyno(guild, channel.id, startDateTime=start, endDateTime=end, limit=limit)
    for user in bannedUsers:
        print(user)
        try:
            await guild.unban(user)
            unbanned = True
        except:
            banFails += 1
            continue
        if unbanned:
            try:
                await user.send(content=f'It appears that you were wrongfully banned in the server "{guild.name}" You have been unbanned, and can rejoin using this link:\n{invite.url}')
                reInvited = True
            except:
                print(f'Failed to send invite to {user.name}, passing.')
                failCount += 1
        logger.logPass(bot.get_user(user), bot.get_user(user), unbanned, reInvited)

    logFile = discord.File(logger.writeLog())
    await ctx.author.send(content=f'Finished unbanning {len(bannedUsers) - banFails} out of {len(bannedUsers)} banned user(s) from the server {guild.name}.\nFailed to message {failCount} user(s) with a new invite.\nA full log of the run has been attached to this message.', file=logFile)
    return

@bot.command(name='kill')
@isMod()
async def kill(ctx):
    await ctx.send("I'm dying...")
    await bot.close()
    return

@bot.command(name='restart')
#@bot.is_owner()
async def restart(ctx):
    await ctx.send('Restarting...')
    await bot.close()
    os.system('pipenv run python src/bot.py')
    return

@bot.command(name='addMod')
@isOwner()
async def addModerator(ctx):
    guild = ctx.guild
    message = ctx.message
    guildConfig = readConfig(guild)
    try:
        modList = guildConfig['modList']
    except:
        modList = []
    for mention in message.mentions:
        mod = mention.id
        modList.append(mod)
    guildConfig['modList'] = modList
    with open(f'guilds/{guild.id}.json', 'wt') as writeConfig:
        writeConfig.write(json.dumps(guildConfig, indent=2))
    await ctx.send('Mods have been added!')
    return

if __name__ == '__main__':
    bot.run(os.environ['TOKEN'])
