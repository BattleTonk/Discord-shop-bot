import discord
import json
from database_manager_lama34 import DatabaseManager

with open("config.json", "r", encoding="UTF-8") as file:
    CONFIG = json.loads(file.read())

database_manager = DatabaseManager()
BANANA_TYPES = database_manager.get_items()

intents = discord.Intents.all()
client = discord.Client(command_prefix='$', intents=intents)


def create_order_info_embed(order_id:int, user_id:int, item_to_buy:str) -> discord.Embed:
    embed = discord.Embed(color=discord.Color.random(), title=f"Order number {order_id}")

    embed.add_field(name="Client:",
                    value=f"<@{user_id}>",
                    inline=False)

    embed.add_field(name="Item:",
                    value=f"**{item_to_buy}**",
                    inline=False)
    return embed


def create_banana_embed(banana_name, banana_image, banana_cost, banana_description) -> discord.Embed:
    banana_embed = discord.Embed(color=discord.Color.random(), title=banana_name)
    banana_embed.set_image(url=banana_image)
    banana_embed.add_field(name="Price:",
                           value=f"{banana_cost}$",
                           inline=False)
    if len(banana_description) > 0:
        banana_embed.add_field(name="Description:",
                               value=banana_description,
                               inline=False)
    return banana_embed


class BananaView(discord.ui.View):
    def __init__(self, banana_id):
        super().__init__(timeout=None)
        self.banana_id = banana_id
        self.add_item(discord.ui.Button(label="Buy", style=discord.ButtonStyle.green, emoji="🛒", custom_id=f"buy{banana_id}"))
        self.children[0].callback = self.buy_item_callback

    async def buy_item_callback(self, interaction):
        order_id, channel_id = database_manager.create_order(interaction.user.id, self.banana_id)
        guild = interaction.message.guild
        channel_category = interaction.channel.category

        if channel_id is None:
            shop_role = discord.utils.get(guild.roles, name=CONFIG["ticket_access_role"])

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                shop_role: discord.PermissionOverwrite(read_messages=True)
            }
            for user_id in CONFIG["shop_owners"]:
                overwrites[client.get_user(user_id)] = discord.PermissionOverwrite(read_messages=True)

            if channel_category is not None:
                channel = await guild.create_text_channel(
                    f"{BANANA_TYPES[self.banana_id][0]}-{order_id}",
                    overwrites=overwrites,
                    category=channel_category
                )
            else:
                channel = await guild.create_text_channel(
                    f"{BANANA_TYPES[self.banana_id][0]}-{order_id}",
                    overwrites=overwrites
                )

            embed = create_order_info_embed(order_id, interaction.user.id, BANANA_TYPES[self.banana_id][0])

            msg = await channel.send(embed=embed, view=BananaOrderView(order_id))
            database_manager.set_order_channel_and_message_id(order_id, channel.id, msg.id)

            await interaction.response.send_message(f"Your order: <#{channel.id}>", ephemeral=True)
            return

        channel = guild.get_channel(channel_id)
        if channel is None:
            shop_role = discord.utils.get(guild.roles, name=CONFIG["ticket_access_role"])

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                shop_role: discord.PermissionOverwrite(read_messages=True)
            }
            for user_id in CONFIG["shop_owners"]:
                overwrites[client.get_user(user_id)] = discord.PermissionOverwrite(read_messages=True)

            if channel_category is not None:
                channel = await guild.create_text_channel(
                    f"{BANANA_TYPES[self.banana_id][0]}-{order_id}",
                    overwrites=overwrites,
                    category=channel_category
                )
            else:
                channel = await guild.create_text_channel(
                    f"{BANANA_TYPES[self.banana_id][0]}-{order_id}",
                    overwrites=overwrites
                )

            embed = create_order_info_embed(order_id, interaction.user.id, BANANA_TYPES[self.banana_id][0])

            msg = await channel.send(embed=embed, view=BananaOrderView(order_id))
            database_manager.set_order_channel_and_message_id(order_id, channel.id, msg.id)

            await interaction.response.send_message(f"Your order: <#{channel.id}>", ephemeral=True)
            return

        await interaction.response.send_message(f"You already have an order: <#{channel.id}>", ephemeral=True)


class BananaOrderDeleteView(discord.ui.View):
    @discord.ui.button(label="Delete this channel", style=discord.ButtonStyle.red, emoji="🔥")
    async def button_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            await interaction.channel.delete()
            return
        await interaction.response.send_message(content="# You don't have the permission to delete the channel", ephemeral=True)


class BananaOrderView(discord.ui.View):
    def __init__(self, order_id):
        super().__init__()
        self.order_id = order_id

    @discord.ui.button(label="Close the order", style=discord.ButtonStyle.red, emoji="🔥")
    async def button_callback(self, interaction: discord.Interaction, button):
        if discord.utils.get(interaction.guild.roles, name=CONFIG["ticket_access_role"]) in interaction.guild.get_member(interaction.user.id).roles or interaction.user.id in CONFIG["shop_owners"]:
            discord_id, channel_id, msg_id = database_manager.get_order(self.order_id)
            order_message = await interaction.channel.fetch_message(msg_id)

            shop_role = discord.utils.get(interaction.guild.roles, name=CONFIG["ticket_access_role"])

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                client.get_user(discord_id): discord.PermissionOverwrite(read_messages=False),
                shop_role: discord.PermissionOverwrite(read_messages=True)
            }
            for user_id in CONFIG["shop_owners"]:
                overwrites[client.get_user(user_id)] = discord.PermissionOverwrite(read_messages=True)

            await interaction.channel.edit(overwrites=overwrites)
            database_manager.close_order(self.order_id)
            await order_message.edit(view=BananaOrderDeleteView())
            await interaction.response.send_message("# THE ORDER IS CLOSED")
            await interaction.channel.edit(name=f"Closed-{interaction.channel.name}")
            return
        await interaction.response.send_message(content="# You don't have the permission to close the order", ephemeral=True)


class AdminPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add item", style=discord.ButtonStyle.primary, custom_id="addItem")
    async def add_banana_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            await interaction.response.send_modal(AddBananaModel())

    @discord.ui.button(label="Remove item", style=discord.ButtonStyle.primary, custom_id="deleteOrder")
    async def remove_banana_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            await interaction.response.send_modal(RemoveBananaModel())

    @discord.ui.button(label="Edit item", style=discord.ButtonStyle.primary, custom_id="redactOrder")
    async def redact_banana_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            await interaction.response.send_modal(RedactBananaModel())

    @discord.ui.button(label="Item list", style=discord.ButtonStyle.primary, custom_id="itemList")
    async def banana_list_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            bananas = ""
            for i in BANANA_TYPES.keys():
                bananas += f"item id: {i}\nitem name: {BANANA_TYPES[i][0]}\nitem price: {BANANA_TYPES[i][2]}\n<=====================================>\n"
            await interaction.response.send_message(content=bananas, ephemeral=True)


class AddBananaModel(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Add item")

        self.add_item(discord.ui.TextInput(label="Name"))
        self.add_item(discord.ui.TextInput(label="Image URL"))
        self.add_item(discord.ui.TextInput(label="Price"))
        self.add_item(discord.ui.TextInput(label="Description", required=False))

    async def on_submit(self, interaction):
        try:
            price = int(str(self.children[2]))
        except ValueError:
            await interaction.response.send_message("The price of the item should be a number", ephemeral=True)
            return
        if price <= 0:
            await interaction.response.send_message("The price of the item should be bigger than zero", ephemeral=True)
            return
        name = str(self.children[0])
        image_url = str(self.children[1])
        description = str(self.children[3])

        new_item_id = database_manager.add_item(name, image_url, price, description)
        BANANA_TYPES[new_item_id] = [name, image_url, price, description]

        await interaction.response.send_message(f"The item is added", ephemeral=True)


class RemoveBananaModel(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Delete item")

        self.add_item(discord.ui.TextInput(label="The item's id"))

    async def on_submit(self, interaction):
        try:
            banana_id = int(str(self.children[0]))
        except ValueError:
            await interaction.response.send_message("The id of the item should be a number", ephemeral=True)
            return
        if banana_id not in BANANA_TYPES:
            await interaction.response.send_message("The id of the item should be bigger than zero", ephemeral=True)
            return

        if str(banana_id) in CONFIG["item_messages_id"]:
            msg_id, channel_id = CONFIG["item_messages_id"][str(banana_id)]
            await (await interaction.guild.get_channel(channel_id).fetch_message(msg_id)).delete()
            del CONFIG["item_messages_id"][str(banana_id)]
            with open("config.json", "w", encoding="UTF-8") as file:
                json.dump(CONFIG, file)

        del BANANA_TYPES[banana_id]
        database_manager.remove_item(banana_id)

        await interaction.response.send_message(f"The item is removed", ephemeral=True)


class RedactBananaModel(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Edit item")

        self.add_item(discord.ui.TextInput(label="The item's id"))
        self.add_item(discord.ui.TextInput(label="New name", required=False))
        self.add_item(discord.ui.TextInput(label="New image URL", required=False))
        self.add_item(discord.ui.TextInput(label="New price", required=False))
        self.add_item(discord.ui.TextInput(label="New description", required=False))

    async def on_submit(self, interaction):
        try:
            banana_id = int(str(self.children[0]))
        except ValueError:
            await interaction.response.send_message("The id of the item should be a number", ephemeral=True)
            return
        if banana_id not in BANANA_TYPES.keys():
            await interaction.response.send_message("Input an id of an existing item", ephemeral=True)
            return

        name_x, url_x, price_x, description_x = database_manager.get_item_by_id(banana_id)

        price = str(self.children[3])
        if price != '':
            try:
                price = int(price)
            except ValueError:
                await interaction.response.send_message("The price of the item should be a number", ephemeral=True)
                return
            if price <= 0:
                await interaction.response.send_message("The price of the item should be bigger than zero",
                                                        ephemeral=True)
                return

            price_x = price
            BANANA_TYPES[banana_id][2] = price
            database_manager.set_items_price(banana_id, price)

        name = str(self.children[1])
        if name != '':
            name_x = name
            BANANA_TYPES[banana_id][0] = name
            database_manager.set_items_name(banana_id, name)

        image_url = str(self.children[2])
        if image_url != '':
            url_x = image_url
            BANANA_TYPES[banana_id][1] = image_url
            database_manager.set_items_url(banana_id, image_url)

        description = str(self.children[4])
        if description == "none":
            description_x = ''
            BANANA_TYPES[banana_id][3] = ''
            database_manager.set_items_description(banana_id, '')
        elif description != '':
            description_x = description
            BANANA_TYPES[banana_id][3] = description
            database_manager.set_items_description(banana_id, description)

        embed = create_banana_embed(name_x, url_x, price_x, description_x)

        msg_id, channel_id = CONFIG["item_messages_id"][str(banana_id)]
        item_message = await interaction.guild.get_channel(channel_id).fetch_message(msg_id)

        await item_message.edit(embed=embed, view=BananaView(banana_id))

        await interaction.response.send_message(f"The item was successfully edited", ephemeral=True)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.author.id in CONFIG["shop_owners"]:
        if message.content.startswith('$initItem'):
            item_id = message.content.split()
            if len(item_id) == 1:
                return
            try:
                item_id = int(item_id[1])
            except ValueError:
                return
            item = BANANA_TYPES[item_id]

            ##banana_name, banana_image, banana_cost, banana_description = item
            banana_embed = create_banana_embed(*item)

            msg = await message.channel.send(embed=banana_embed, view=BananaView(item_id))

            CONFIG["item_messages_id"][str(item_id)] = (msg.id, message.channel.id)
            with open("config.json", "w", encoding="UTF-8") as file:
                json.dump(CONFIG, file)
            await message.delete()
        elif message.content.startswith('$adminPanel'):
            embed = discord.Embed(color=discord.Color.random())
            embed.add_field(name="Admin panel",
                            value="Odmen",
                            inline=False)
            msg = await message.channel.send(view=AdminPanelView(), embed=embed)
            CONFIG["admin_panel_message_id"] = msg.id
            with open("config.json", "w", encoding="UTF-8") as file:
                json.dump(CONFIG, file)
            await message.delete()


async def setup_hook():
    client.add_view(AdminPanelView(), message_id=CONFIG["admin_panel_message_id"])
    for item_id, (msg_id, _) in CONFIG["item_messages_id"].items():
        client.add_view(BananaView(int(item_id)), message_id=msg_id)


client.setup_hook = setup_hook

with open(".token") as token_file:
    token = token_file.read()
client.run(token)
