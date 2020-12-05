# Dale Schofield
# 12/4/2020
import twitch, discord
import credentials, channels
import datetime, threading, time
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
        if len(message.content.split(' ')) > 2:
            username = ' '.join(message.content.split(' ')[2:])
            await message.channel.send(add_user(username))
        else:
            await message.channel.send("Please enter a user!")

    if message.content.startswith('!announce remove'):
        if len(message.content.split(' ')) > 2:
            username = ' '.join(message.content.split(' ')[2:])
            await message.channel.send(remove_user(username))
        else:
            await message.channel.send("Please enter a user!")

    if message.content.startswith('!announce message'):
        await message.channel.send('Hello!')


@discord_client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(discord_client))
    await discord_client.get_channel(int(channels.command_channel)).send('Hello!')


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
    print("users_to_check: "+str(users_to_check))
    print("already_announced: "+str(already_announced))


def add_user(username):
    return_msg = "add_user Return Message"
    if helix.user(username) is not None:
        cursor = message_db.cursor()
        query = 'SELECT user FROM announce_messages WHERE user=?'
        cursor.execute(query, [username])
        user = cursor.fetchone()
        update_lists = False
        if user is None:
            query = 'INSERT INTO announce_messages VALUES (?,?)'
            cursor.execute(query, (username, ""))

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


def check_alert_users():
    # check channels here
    global users_to_check
    for user in users_to_check:
        channel_state = helix.user(user).is_live


def send_alerts(twitch_user):
    # send alert for the passed user here
    print()


def polling_loop():
    global next_call
    # do stuff here
    next_call = next_call + 1
    threading.Timer(next_call - time.time(), polling_loop).start()


if __name__ == '__main__':
    helix = twitch.Helix(credentials.client_id, credentials.client_secret)
    print(helix.user('ilikepiez5642').is_live)
    update_twitch_user_list()
    discord_client.run(credentials.discord_token)
