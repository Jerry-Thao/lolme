import discord
import riot_api
import overwatch_api
import asyncio
import configparser
import traceback

# not yet used
defaults = {
        }

class DiscordBot(discord.Client):
    def __init__(self, conf_file):
        super(DiscordBot, self).__init__()
        # commands
        self.commands = {
            "commands": self.output_commands,
            "overwatch": self.overwatch_get_profile,
            "rank": self.on_rank,
	        "matchlist":self.on_matchlist
        }

        # read config file
        self.conf = configparser.SafeConfigParser(defaults)
        self.conf.read(conf_file)
        self.discord_token = self.conf.get('Bot', 'discord_token')
        self.riot_key = self.conf.get('Riot', 'key')

        # overwatch api
        self.overwatchobj = overwatch_api.OverwatchApi(self.loop)
        # riot api
        self.robj = riot_api.RiotApi(self.loop, self.riot_key)

    # Override run() so we can remove the required parameter
    def run(self):
        super(DiscordBot, self).run(self.discord_token)

    @asyncio.coroutine
    def on_ready(self):
        print("logged in as {}".format(self.user.name))
        print(self.user.id)
        print("----------")

    @asyncio.coroutine
    def on_message(self, message):
        msg = message.content

        print(message.content)
        print("----------")

        if msg.startswith("!"):
            msg = msg[1:] # strip off the bang
            msg_split = msg.split(' ', 1)

            cmd = msg_split[0]
            if len(msg_split) != 2:
                args = []
            else:
                args = msg_split[1].split()

            if cmd in self.commands:
                try:
                    yield from self.commands[cmd](message, args)
                except Exception as e:
                    yield from self.send_message(message.channel, "Error running command")
                    traceback.print_exc()

    @asyncio.coroutine
    def output_commands(self, message, args):
        response = "```The commands are:\n"
        for cmd in self.commands:
            response = response + "!" + cmd + "\n"
        response = response + "```"
        yield from self.send_message(message.channel, response)

    @asyncio.coroutine
    def overwatch_get_profile(self, message, args):
        overwatch_response = ''

        name = args[0]

        try:
            overwatch_response = yield from self.overwatchobj.get_player_profile(name, message)
        except overwatch_api.OverwatchApiHttpException as e:
            if e.response == 404:
                yield from self.send_message(message.channel, '**Error**: Player not found')
                return
            else:
                raise e

        player_level = overwatch_response['data']['level']
        player_wins = int(overwatch_response['data']['games']['competitive']['wins'])
        player_played = int(overwatch_response['data']['games']['competitive']['played'])
        player_win_rate = player_wins/player_played
        player_win_rate = str(int(round(player_win_rate, 2) * 100)) + "%"
        amount_of_time_played = overwatch_response['data']['playtime']['quick']

        response = "```{}:\n".format(name)
        response += "Player Level: {}\n".format(player_level)
        response += "Player Competitive Win Rate: {}\n".format(player_win_rate)
        response += "Played QuickPlay for: {}\n```".format(amount_of_time_played)
        
        yield from self.send_message(message.channel, response)

    @asyncio.coroutine
    def on_rank(self, message, args):
        if len(args) < 1:
            yield from self.send_message(message.channel, '**Error**: No summoner specified')

        response = ''

        name = ''.join([s.lower() for s in args])

        try:
            sobj = yield from self.robj.get_summoner_by_name([name])
            response += "*{}*\n**level**: {}\n".format(sobj[name]['name'], sobj[name]['summonerLevel'])
        except riot_api.RiotApiHttpException as e:
            if e.response == 404:
                yield from self.send_message(message.channel, '**Error**: Summoner not found')
                return
            else:
                raise e

        try:
            lobj = yield from self.robj.get_league_by_summonerid(sobj[name]['id'])
            rank = 'Unranked'
            for league in lobj[str(sobj[name]['id'])]:
                if league['queue'] == 'RANKED_SOLO_5x5':
                    rank = league['tier'].lower()
                    for summoner in league['entries']:
                        if summoner['playerOrTeamId'] == str(sobj[name]['id']):
                            rank += summoner['division']
            response += '**rank**: ' + rank + '\n'
        except riot_api.RiotApiHttpException as e:
            if e.response == 404:
                response += '**rank**: Unranked\n'
            else:
                raise e

        yield from self.send_message(message.channel, response)

    @asyncio.coroutine
    def test_fxn(self,message,args):
        yield from self.send_message(message.channel, "Ddayknight is gold 1, don't judge @OnVar#4902")

    @asyncio.coroutine
    def on_matchlist(self,message,args):
        if len(args) < 1:
            yield from self.send_message(message.channel, '**Error**: No summoner specified')

        response = ''

        name = ''.join([s.lower() for s in args])

        try:
            sobj = yield from self.robj.get_summoner_by_name([name])
            response += "**{}'s Recent Matches**: \n".format(sobj[name]['name'])
        except riot_api.RiotApiHttpException as e:
            if e.response == 404:
                yield from self.send_message(message.channel, '**Error**: Summoner not found')
                return
            else:
                raise e

        matchlist = yield from self.robj.get_matchlist(summonerID=sobj[name]['id'], region='na')
        
        for matchIndex in range(len(matchlist["matches"])):   
            response += (str(matchlist["matches"][matchIndex]["matchId"]))
#        for match in matchlist["matches"]:
#           response += (str(match) + "\n")

        yield from self.send_message(message.channel, response)


bot = DiscordBot('bot.conf')
bot.run()
