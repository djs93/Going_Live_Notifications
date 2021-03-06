# Dale Schofield
# 12/4/2020
import asyncio

import requests
import twitch, discord
import credentials, channels
import datetime, threading, time, random
import sqlite3

discord_client = discord.Client()
next_call = time.time()
message_db = sqlite3.connect('message_db.db')
users_to_check = []
already_announced = {}


@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    if message.channel.id != channels.command_channel and message.author != message.channel.guild.owner:
        return

    if message.content.startswith('!announce add'):
        if len(message.content.split(' ')) >= 5:  # we have person, color, and message
            username = message.content.split(' ')[2]
            new_color = message.content.split(' ')[3].lstrip('#')
            new_message = ' '.join(message.content.split(' ')[4:])
            await message.channel.send(add_user_all(username, new_color, new_message))
        elif len(message.content.split(' ')) == 4:  # we have person and color
            username = message.content.split(' ')[2]
            new_color = message.content.split(' ')[3].lstrip('#')
            await message.channel.send(add_user_with_color(username, new_color))
        elif len(message.content.split(' ')) > 2:
            username = ' '.join(message.content.split(' ')[2:])
            await message.channel.send(add_user(username.lower()))
        elif len(message.content.split(' ')) == 2:
            await message.channel.send("Usage: !announce add <twitch username>\nNot case-sensitive!")
            await message.channel.send("Usage: !announce add <twitch username> <hex color with #> <going live message>")
        else:
            await message.channel.send("Please enter a user!")

    if message.content.startswith('!announce remove'):
        if len(message.content.split(' ')) > 2:
            username = ' '.join(message.content.split(' ')[2:])
            await message.channel.send(remove_user(username.lower()))
        elif len(message.content.split(' ')) == 2:
            await message.channel.send("Usage: !announce remove <twitch_username>\nNot case-sensitive!")
        else:
            await message.channel.send("Please enter a user!")

    if message.content.startswith('!announce message'):
        if len(message.content.split(' ')) >= 4:
            username = message.content.split(' ')[2]
            new_message = ' '.join(message.content.split(' ')[3:])
            await message.channel.send(modify_message(username.lower(), new_message))
        elif len(message.content.split(' ')) == 2:
            await message.channel.send("Usage: !announce message <twitch_username> <new_message>"
                                       "\nTwitch username is not case-sensitive!"
                                       "\nNew message can be separated by spaces")
        else:
            await message.channel.send("Please enter a message!")

    if message.content.startswith('!announce color'):
        if len(message.content.split(' ')) >= 4:
            username = message.content.split(' ')[2]
            new_color = message.content.split(' ')[3].lstrip('#')
            if len(new_color) != 6:
                await message.channel.send("Invalid hex color length!")
            else:
                await message.channel.send(modify_color(username.lower(), new_color))
        elif len(message.content.split(' ')) == 2:
            await message.channel.send("Usage: !announce color <twitch_username> #<new_hex_color>"
                                       "\nTwitch username is not case-sensitive!"
                                       "\nColor must be in hex and!")
        else:
            await message.channel.send("Please enter a color!")

    if message.content.startswith('!announce manual'):
        if len(message.content.split(' ')) > 2:
            username = ' '.join(message.content.split(' ')[2:])
            await send_alert_manual(username, message.author.mention)
        elif len(message.content.split(' ')) == 2:
            await message.channel.send("Usage: !announce manual <twitch_username>")


@discord_client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(discord_client))
    await discord_client.get_channel(int(channels.command_channel)).send('Hello!')
    update_twitch_user_list()
    # await polling_loop()


def update_twitch_user_list():
    global users_to_check
    cursor = message_db.cursor()
    query = 'SELECT user FROM announce_messages'
    cursor.execute(query)
    users_to_check = []
    for user_tuple in cursor.fetchall():
        users_to_check.append(user_tuple[0])
    cursor.close()
    for user in users_to_check:
        if user not in already_announced:
            already_announced[user] = False
    print("users_to_check: " + str(users_to_check))
    print("already_announced: " + str(already_announced))


def add_user(username):
    return_msg = "add_user Return Message"
    if helix.user(username) is not None:
        cursor = message_db.cursor()
        query = 'SELECT user FROM announce_messages WHERE user=?'
        cursor.execute(query, [username])
        user = cursor.fetchone()
        update_lists = False
        if user is None:
            query = 'INSERT INTO announce_messages VALUES (?,?,?)'
            cursor.execute(query, (username, None, None))

            query = 'SELECT user FROM announce_messages WHERE user = ?'
            cursor.execute(query, [username])
            user = cursor.fetchone()

            if user is not None:
                return_msg = "Added user " + username + "!"
                message_db.commit()
                update_lists = True
            else:
                return_msg = "Error adding user " + username
        else:
            return_msg = "User " + username + " already exists!"

        cursor.close()

        if update_lists is True:
            update_twitch_user_list()

    else:
        return_msg = "User " + username + " does not exist on Twitch!"

    return return_msg


def add_user_with_color(username, new_color):
    curr_msg = add_user(username)
    if curr_msg.split(' ')[0] != "Added":
        return curr_msg

    curr_msg = modify_color(username, new_color)
    if curr_msg[0:len(username)] != username:
        return curr_msg

    return username + " has been added with color #" + new_color + "!"


def add_user_all(username, new_color, new_msg):
    curr_msg = add_user(username)
    if curr_msg.split(' ')[0] != "Added":
        return curr_msg

    curr_msg = modify_color(username, new_color)
    if curr_msg[0:len(username)] != username:
        return curr_msg

    curr_msg = modify_message(username, new_msg)
    if curr_msg[0:len(username)] != username:
        return curr_msg

    return username + " has been added with color #" + new_color + " and message " + new_msg + "!"


def remove_user(username):
    return_msg = "remove_user Return Message"
    if helix.user(username) is not None:
        cursor = message_db.cursor()
        query = 'SELECT user FROM announce_messages WHERE user=?'
        cursor.execute(query, [username])
        user = cursor.fetchone()
        update_lists = False
        if user is None:
            return_msg = "User " + username + " is not in the announcement database!"
        else:
            query = 'DELETE FROM announce_messages WHERE user = ?'
            cursor.execute(query, [username])

            query = 'SELECT user FROM announce_messages WHERE user = ?'
            cursor.execute(query, [username])
            user = cursor.fetchone()

            if user is None:
                return_msg = "Removed user " + username + "!"
                message_db.commit()
                if username in already_announced:
                    del already_announced[username]
                update_lists = True
            else:
                return_msg = "Error adding user " + username

        cursor.close()

        if update_lists is True:
            update_twitch_user_list()

    else:
        return_msg = "User " + username + " does not exist on Twitch!"

    return return_msg


def modify_message(username, new_message):
    return_msg = "modify_message Return Message"
    if helix.user(username) is not None:
        cursor = message_db.cursor()
        query = 'SELECT user FROM announce_messages WHERE user=?'
        cursor.execute(query, [username])
        user = cursor.fetchone()
        if user is not None:
            query = 'UPDATE announce_messages SET announce_msg = ? WHERE user = ?'
            cursor.execute(query, (new_message, username))

            query = 'SELECT announce_msg FROM announce_messages WHERE user = ?'
            cursor.execute(query, [username])
            msg = cursor.fetchone()

            if msg is not None:
                return_msg = username + "'s announcement message is now: " + msg[0]
                message_db.commit()
            else:
                return_msg = "Error editing user message for " + username
        else:
            return_msg = "User " + username + " is not in the announcement database!"

        cursor.close()
    else:
        return_msg = "User " + username + " does not exist on Twitch!"

    return return_msg


def modify_color(username, new_color):
    return_msg = "modify_color Return Message"
    if helix.user(username) is not None:
        cursor = message_db.cursor()
        query = 'SELECT user FROM announce_messages WHERE user=?'
        cursor.execute(query, [username])
        user = cursor.fetchone()
        if user is not None:
            query = 'UPDATE announce_messages SET color = ? WHERE user = ?'
            cursor.execute(query, (str(new_color), username))

            query = 'SELECT color FROM announce_messages WHERE user = ?'
            cursor.execute(query, [username])
            color = cursor.fetchone()

            if color is not None:
                return_msg = username + "'s announcement color is now: #" + color[0]
                message_db.commit()
            else:
                return_msg = "Error editing user color for " + username
        else:
            return_msg = "User " + username + " is not in the announcement database!"
        cursor.close()
    else:
        return_msg = "User " + username + " does not exist on Twitch!"

    return return_msg


def get_user_color(username):
    return_color = random.randint(0, 16777215)
    if helix.user(username) is not None:
        cursor = message_db.cursor()
        query = 'SELECT user FROM announce_messages WHERE user=?'
        cursor.execute(query, [username])
        user = cursor.fetchone()
        if user is not None:
            cursor = message_db.cursor()
            query = 'SELECT color FROM announce_messages WHERE user = ?'
            cursor.execute(query, [username])
            color_fetch = cursor.fetchone()

            if color_fetch is not None and color_fetch[0] is not None:
                return_color = int("0x" + color_fetch[0], 0)
        cursor.close()
    return return_color


def get_random_color():
    return random.randint(0, 16777215);


def get_user_message(username):
    return_msg = username + " is live!"
    if helix.user(username) is not None:
        cursor = message_db.cursor()
        query = 'SELECT user FROM announce_messages WHERE user=?'
        cursor.execute(query, [username])
        user = cursor.fetchone()
        if user is not None:
            cursor = message_db.cursor()
            query = 'SELECT announce_msg FROM announce_messages WHERE user = ?'
            cursor.execute(query, [username])
            msg_fetch = cursor.fetchone()

            if msg_fetch is not None and msg_fetch[0] is not None:
                return_msg = msg_fetch[0]
        cursor.close()

    return return_msg


async def check_alert_users():
    # check channels here
    global users_to_check
    for user in users_to_check:
        channel_state = helix.user(user).is_live
        if channel_state is True and already_announced[user] is False:  # User went online and we need to announce
            already_announced[user] = True
            await send_alert(user)
        elif channel_state is False and already_announced[user] is True:  # User went offline
            already_announced[user] = False
    now = datetime.datetime.now()
    print("[" + now.strftime("%H:%M:%S") + "] users_to_check: " + str(already_announced))


async def send_alert(twitch_user):
    # send alert for the passed user here
    user = helix.user(twitch_user)
    if user is None:
        error = "Alert error, user " + twitch_user + " doesn't exist on Twitch!"
        discord_client.get_channel(channels.command_channel).send(error)
        return
    try:
        if user.is_live is False:
            error = "Alert error, user " + twitch_user + " isn't live on Twitch but we tried to send an alert anyway!"
            discord_client.get_channel(channels.command_channel).send(error)
            already_announced[twitch_user] = False
            return
    except twitch.helix.resources.streams.StreamNotFound as error:
        error_msg = "Alert error, user " + twitch_user + " doesn't have a stream on Twitch but we tried to send an alert anyway!"
        discord_client.get_channel(channels.command_channel).send(error_msg)
        already_announced[twitch_user] = False
        return
    except Exception as error:
        template = "An exception of type {0} occurred in send_alert."
        message = template.format(type(error).__name__)
        discord_client.get_channel(channels.command_channel).send(message)
    finally:
        title = user.stream.title
        url = "https://www.twitch.tv/" + twitch_user.lower()
        user_color = get_user_color(twitch_user)
        embed = discord.Embed(title=title, url=url, color=user_color)
        embed.set_author(name=user.display_name, url=url, icon_url=user.profile_image_url)
        embed.set_thumbnail(url=user.profile_image_url)
        thumb_url = user.stream.thumbnail_url.split('{')[0]
        thumb_url += "1280x720.jpg"
        embed.set_image(url=thumb_url)
        embed.add_field(name="Game", value=helix.game(id=user.stream.game_id).name, inline=True)

        send_msg = get_user_message(twitch_user)
        for channel_id in channels.notif_channels:
            await discord_client.get_channel(channel_id).send(send_msg, embed=embed)
            print("Sent alert in " + discord_client.get_channel(channel_id).name + "!")


async def send_alert_manual(twitch_user, caller):
    # send alert for the passed user here
    user = helix.user(twitch_user)
    if user is None:
        error = "Alert error, user " + twitch_user + " doesn't exist on Twitch!"
        discord_client.get_channel(int(channels.command_channel)).send(error)
        return
    if user.is_live is False:
        error = "User " + twitch_user + " is not live on Twitch!"
        discord_client.get_channel(int(channels.command_channel)).send(error)
    title = user.stream.title
    url = "https://www.twitch.tv/" + twitch_user.lower()
    if user in users_to_check:
        user_color = get_user_color(twitch_user)
    else:
        user_color = get_random_color()
    embed = discord.Embed(title=title, url=url, color=user_color)
    embed.set_author(name=user.display_name, url=url, icon_url=user.profile_image_url)
    embed.set_thumbnail(url=user.profile_image_url)
    thumb_url = user.stream.thumbnail_url.split('{')[0]
    thumb_url += "1280x720.jpg"
    embed.set_image(url=thumb_url)
    embed.add_field(name="Game", value=helix.game(id=user.stream.game_id).name, inline=True)
    if user in users_to_check:
        user_msg = get_user_message(twitch_user)
        for channel_id in channels.notif_channels:
            await discord_client.get_channel(channel_id).send(user_msg, embed=embed)
    else:
        for channel_id in channels.notif_channels:
            await discord_client.get_channel(channel_id).send(
                caller + " wanted everybody to know that " + user.display_name + " is live!",
                embed=embed
            )


async def polling_loop():
    global next_call
    # do stuff here
    try:
        await check_alert_users()
    except requests.exceptions.ConnectionError as error:
        await discord_client.get_channel(channels.command_channel).send('Connection error! (Probably rate limit)\n'
                                                                        'Here\'s the error: ' + error.strerror)
    next_call = next_call + 7
    await asyncio.sleep(next_call - time.time())
    await polling_loop()


async def poll():
    global next_call, helix
    # do stuff here
    try:
        await check_alert_users()
    except requests.ConnectionError as error:
        await discord_client.get_channel(channels.command_channel).send('Connection error!\n'
                                                                        'Here\'s the error: ' + error.response.text)
        # helix = twitch.Helix(credentials.client_id, credentials.client_secret)
    except requests.HTTPError as error:
        # helix = twitch.Helix(credentials.client_id, credentials.client_secret)
        if error.response.status_code == 502:
            await discord_client.get_channel(channels.command_channel).send('Bad gateway error! Retrying in 7 seconds.')

    next_call = next_call + 7
    await asyncio.sleep(next_call - time.time())

async def background_task():
    await discord_client.wait_until_ready()
    while not discord_client.is_closed():
        try:
            await poll()
        except Exception as error:
            template = "An exception of type {0} occurred while looping."
            message = template.format(type(error).__name__)
            await discord_client.get_channel(channels.command_channel).send(message)

if __name__ == '__main__':
    helix = twitch.Helix(credentials.client_id, credentials.client_secret)
    discord_client.loop.create_task(background_task())
    discord_client.run(credentials.discord_token)
