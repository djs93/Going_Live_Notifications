# Dale Schofield
# 12/4/2020
import asyncio

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

    if message.content.startswith('!announce add'):
        # TODO add option where you can specify person, color, and live message all in one go
        # (useful for if they're already live)
        if len(message.content.split(' ')) > 2:
            username = ' '.join(message.content.split(' ')[2:])
            await message.channel.send(add_user(username.lower()))
        elif len(message.content.split(' ')) == 2:
            await message.channel.send("Usage: !announce add <twitch_username>\nNot case-sensitive!")
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
    await polling_loop()



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
            await send_alert(user)
            already_announced[user] = True
        elif channel_state is False and already_announced[user] is True:  # User went offline
            already_announced[user] = False


async def send_alert(twitch_user):
    # send alert for the passed user here
    user = helix.user(twitch_user)
    if user is None:
        error = "Alert error, user " + twitch_user + " doesn't exist on Twitch!"
        discord_client.get_channel(int(channels.command_channel)).send(error)
        return
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

    await discord_client.get_channel(int(channels.command_channel)).send(get_user_message(twitch_user), embed=embed)


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
        await discord_client.get_channel(int(channels.command_channel)).send(get_user_message(twitch_user), embed=embed)
    else:
        await discord_client.get_channel(int(channels.command_channel)).send(
            caller + " wanted everybody to know that " + user.display_name + " is live!",
            embed=embed
        )


async def polling_loop():
    global next_call
    # do stuff here
    update_twitch_user_list()
    await check_alert_users()
    next_call = next_call + 6
    await asyncio.sleep(next_call - time.time())
    await polling_loop()


if __name__ == '__main__':
    helix = twitch.Helix(credentials.client_id, credentials.client_secret)
    discord_client.run(credentials.discord_token)
