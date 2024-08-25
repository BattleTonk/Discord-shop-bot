import discord
from discord.ext import commands
import json
from database_manager import DatabaseManager

with open("config.json", "r", encoding="UTF-8") as file:
    CONFIG = json.loads(file.read())

database_manager = DatabaseManager()
BANANA_TYPES = database_manager.get_items()

intents = discord.Intents.all()
client = discord.Client(command_prefix='$', intents=intents)


def create_order_info_embed(order_id:int, user_id:int, minecraft_nickname:str, cart:list) -> discord.Embed:
    embed = discord.Embed(color=discord.Color.random(), title=f"Заказ номер {order_id}")

    embed.add_field(name="Заказчик:",
                    value=f"<@{user_id}>",
                    inline=False)

    embed.add_field(name="Ник заказчика:",
                    value=f"{minecraft_nickname}",
                    inline=False)

    embed.add_field(name="\u200b",
                    value=f"**Корзина заказчика:**",
                    inline=False)

    embed.add_field(name="Название товара:", value="\n".join([BANANA_TYPES[i[0]][0] for i in cart]))
    embed.add_field(name="Количество:", value="\n".join([str(i[1]) for i in cart]))
    embed.add_field(name="Стоимость:",
                    value="\n".join([str(i[1] * BANANA_TYPES[i[0]][2]) + " рублей" for i in cart]))
    embed.add_field(name="Итого:",
                    value=f"**{sum([i[1] * BANANA_TYPES[i[0]][2] for i in cart])} рублей**",
                    inline=False)
    return embed


class MyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Сорта бананов", style=discord.ButtonStyle.primary, emoji="🏪",
                       custom_id="kits_assortment")
    async def banana_sorts_button_callback(self, interaction, button):
        bananas_index = list(BANANA_TYPES.keys())
        banana_name, banana_image, banana_cost = BANANA_TYPES[bananas_index[0]]
        banana_embed = discord.Embed(color=discord.Color.random(), title=banana_name)
        banana_embed.set_image(url=banana_image)
        banana_embed.add_field(name="Цена:",
                               value=f"{banana_cost} рублей",
                               inline=False)
        await interaction.response.send_message(embed=banana_embed, view=BananaView(bananas_index[0]), ephemeral=True)
        for i in range(1, len(bananas_index)):
            banana_name, banana_image, banana_cost = BANANA_TYPES[bananas_index[i]]
            banana_embed = discord.Embed(color=discord.Color.random(), title=banana_name)
            banana_embed.set_image(url=banana_image)
            banana_embed.add_field(name="Цена:",
                                   value=f"{banana_cost} рублей",
                                   inline=False)
            await interaction.followup.send(embed=banana_embed, view=BananaView(bananas_index[i]), ephemeral=True)

    @discord.ui.button(label="Корзина", style=discord.ButtonStyle.primary, emoji="🗑", custom_id="cart")
    async def cart_button_callback(self, interaction, button):
        cart = database_manager.get_cart(interaction.user.id)

        embed = discord.Embed(color=discord.Color.random(), title="Корзина")

        if len(cart) == 0:
            embed.add_field(name="Содержание:",
                                   value=f"Пусто",
                                   inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed.add_field(name="Название товара:", value="\n".join([BANANA_TYPES[i[0]][0] for i in cart]))
            embed.add_field(name="Количество:", value="\n".join([str(i[1]) for i in cart]))
            embed.add_field(name="Стоимость:",
                                   value="\n".join([str(i[1] * BANANA_TYPES[i[0]][2]) + " рублей" for i in cart]))
            embed.add_field(name="Итого:",
                                   value=f"**{sum([i[1] * BANANA_TYPES[i[0]][2] for i in cart])} рублей**",
                                   inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True, view=CartView())

    @discord.ui.button(label="Купить", style=discord.ButtonStyle.primary, emoji="💵", custom_id="buy")
    async def buy_button_callback(self, interaction: discord.Interaction, button):
        cart = database_manager.get_cart(interaction.user.id)

        if len(cart) == 0:
            await interaction.response.send_message("Чтобы открыть заказ надо заполнить корзину", ephemeral=True)
            return

        order_id = database_manager.create_order(interaction.user.id)

        guild = interaction.message.guild
        order_channel = discord.utils.get(guild.channels, name=f"заказ-{order_id}")
        if order_channel is None:
            await interaction.response.send_modal(BuyModal(order_id))
            return

        await interaction.response.send_message(f"Ваш заказ: <#{order_channel.id}>", ephemeral=True)


class BananaView(discord.ui.View):
    def __init__(self, banana_id):
        super().__init__()
        self.banana_id = banana_id

    @discord.ui.button(label="Добавить в корзину", style=discord.ButtonStyle.primary, emoji="➕")
    async def button_callback(self, interaction, button):
        await interaction.response.send_modal(BananaOrderModal(self.banana_id))


class BananaOrderView(discord.ui.View):
    def __init__(self, order_id):
        super().__init__()
        self.order_id = order_id

    @discord.ui.button(label="Закрыть заказ", style=discord.ButtonStyle.primary, emoji="🔥")
    async def button_callback(self, interaction: discord.Interaction, button):
        if discord.utils.get(interaction.guild.roles, name=CONFIG["ticket_access_role"]) in interaction.guild.get_member(interaction.user.id).roles or interaction.user.id in CONFIG["shop_owners"]:
            discord_id, _, _ = database_manager.get_order(self.order_id)
            database_manager.close_order(self.order_id)
            database_manager.clear_cart(discord_id)
            await interaction.response.send_message("# ЗАКАЗ ЗАКРЫТ(канал удалите сами)")
            await interaction.channel.edit(name=f"Закрыт-заказ-{self.order_id}")
            return
        await interaction.response.send_message(content="# У вас нет полномочий на закрытие заказа", ephemeral=True)


class AdminPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Добавить товар", style=discord.ButtonStyle.primary, custom_id="addItem")
    async def add_banana_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            await interaction.response.send_modal(AddBananaModel())

    @discord.ui.button(label="Удалить товар", style=discord.ButtonStyle.primary, custom_id="deleteOrder")
    async def remove_banana_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            await interaction.response.send_modal(RemoveBananaModel())

    @discord.ui.button(label="Редектировать товар", style=discord.ButtonStyle.primary, custom_id="redactOrder")
    async def redact_banana_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            await interaction.response.send_modal(RedactBananaModel())

    @discord.ui.button(label="Список товаров", style=discord.ButtonStyle.primary, custom_id="itemList")
    async def banana_list_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id in CONFIG["shop_owners"]:
            bananas = ""
            for i in BANANA_TYPES.keys():
                bananas += f"id товара: {i}\nназвание товара: {BANANA_TYPES[i][0]}\nЦена товара: {BANANA_TYPES[i][2]}\n<=====================================>\n"
            await interaction.response.send_message(content=bananas, ephemeral=True)


class AddBananaModel(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Добавление товара")

        self.add_item(discord.ui.TextInput(label="Название"))
        self.add_item(discord.ui.TextInput(label="Ссылка на изображение"))
        self.add_item(discord.ui.TextInput(label="Цена"))

    async def on_submit(self, interaction):
        try:
            price = int(str(self.children[2]))
        except ValueError:
            await interaction.response.send_message("Цена товара должна быть числом", ephemeral=True)
            return
        if price <= 0:
            await interaction.response.send_message("Цена товара должна быть больше нуля", ephemeral=True)
            return
        name = str(self.children[0])
        image_url = str(self.children[1])

        new_item_id = database_manager.add_item(name, image_url, price)
        BANANA_TYPES[new_item_id] = [name, image_url, price]

        await interaction.response.send_message(f"Товар добавлен", ephemeral=True)


class RemoveBananaModel(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Удаление товара")

        self.add_item(discord.ui.TextInput(label="id товара"))

    async def on_submit(self, interaction):
        try:
            banana_id = int(str(self.children[0]))
        except ValueError:
            await interaction.response.send_message("Введите число", ephemeral=True)
            return
        if banana_id not in BANANA_TYPES:
            await interaction.response.send_message("Введите id существующего товара", ephemeral=True)
            return

        del BANANA_TYPES[banana_id]
        database_manager.remove_item(banana_id)

        await interaction.response.send_message(f"Товар удалён", ephemeral=True)


class RedactBananaModel(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Редактирование товара")

        self.add_item(discord.ui.TextInput(label="id товара"))
        self.add_item(discord.ui.TextInput(label="Название", required=False))
        self.add_item(discord.ui.TextInput(label="Ссылка на изображение", required=False))
        self.add_item(discord.ui.TextInput(label="Цена", required=False))

    async def on_submit(self, interaction):
        try:
            banana_id = int(str(self.children[0]))
        except ValueError:
            await interaction.response.send_message("Id товара должен быть числом", ephemeral=True)
            return
        if banana_id < 0 or banana_id >= len(CONFIG["banana_types"]):
            await interaction.response.send_message("Введите id существующего товара", ephemeral=True)
            return

        price = str(self.children[3])
        if price != '':
            try:
                price = int(price)
            except ValueError:
                await interaction.response.send_message("Цена товара должна быть числом", ephemeral=True)
                return
            if price <= 0:
                await interaction.response.send_message("Цена товара должна быть больше нуля", ephemeral=True)
                return

            BANANA_TYPES[banana_id][2] = price
            database_manager.set_items_price(banana_id, price)

        name = str(self.children[1])
        if name != '':
            BANANA_TYPES[banana_id][0] = name
            database_manager.set_items_name(banana_id, name)

        image_url = str(self.children[2])
        if image_url != '':
            BANANA_TYPES[banana_id][1] = image_url
            database_manager.set_items_url(banana_id, image_url)

        await interaction.response.send_message(f"Товар был отредактирован", ephemeral=True)


class BananaOrderModal(discord.ui.Modal):
    def __init__(self, banana_id):
        super().__init__(title=f"{BANANA_TYPES[banana_id][0]}")
        self.banana_id = banana_id

        self.add_item(discord.ui.TextInput(label="Количество бананов", max_length=3))

    async def on_submit(self, interaction):
        try:
            amount = int(str(self.children[0]))
        except ValueError:
            await interaction.response.send_message("Введите число большее или равное нулю", ephemeral=True)
            return
        if amount < 0:
            await interaction.response.send_message("Введите число большее или равное нулю", ephemeral=True)
            return
        database_manager.update_or_create_cart(interaction.user.id, [self.banana_id, amount])
        await interaction.response.send_message(f"{amount} {BANANA_TYPES[self.banana_id][0]} находится в вашей корзине",
                                                ephemeral=True)

        ret = database_manager.get_order_by_discord_id(interaction.user.id)
        if ret is None:
            return
        order_id, minecraft_nickname, order_message_id = ret
        order_channel = discord.utils.get(interaction.message.guild.channels, name=f"заказ-{order_id}")
        if order_channel is None:
            return
        if order_message_id is None:
            return

        order_message = await order_channel.fetch_message(order_message_id)

        cart = database_manager.get_cart(interaction.user.id)

        embed = create_order_info_embed(order_id, interaction.user.id, minecraft_nickname, cart)

        await order_message.edit(embed=embed, view=BananaOrderView(order_id))


class BuyModal(discord.ui.Modal):
    def __init__(self, order_id):
        super().__init__(title="Заполните форму")
        self.order_id = order_id

        self.add_item(discord.ui.TextInput(label="Ваш ник в майнкрафте", max_length=16))

        self.add_item(discord.ui.TextInput(label="Промокод", placeholder="Не обязательно", required=False))

    async def on_submit(self, interaction):
        minecraft_nickname = str(self.children[0])
        database_manager.set_order_minecraft_nickname(self.order_id, minecraft_nickname)

        guild = interaction.message.guild
        shop_role = discord.utils.get(guild.roles, name=CONFIG["ticket_access_role"])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
            shop_role: discord.PermissionOverwrite(read_messages=True)
        }
        for user_id in CONFIG["shop_owners"]:
            overwrites[client.get_user(user_id)] = discord.PermissionOverwrite(read_messages=True)

        channel = await guild.create_text_channel(
            f"заказ-{self.order_id}",
            overwrites=overwrites
        )

        cart = database_manager.get_cart(interaction.user.id)

        embed = create_order_info_embed(self.order_id, interaction.user.id, minecraft_nickname, cart)

        msg = await channel.send(embed=embed, view=BananaOrderView(self.order_id))
        database_manager.set_order_channel_id(self.order_id, msg.id)

        await interaction.response.send_message(f"Ваш заказ: <#{channel.id}>", ephemeral=True)


class CartView(discord.ui.View):
    @discord.ui.button(label="Очистить корзину", style=discord.ButtonStyle.primary, emoji="🔥")
    async def button_callback(self, interaction, button):
        database_manager.clear_cart(interaction.user.id)
        await interaction.response.send_message("Корзина очищена",
                                                ephemeral=True)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.author.id in CONFIG["shop_owners"]:
        if message.content.startswith('$init bananaShop'):
            embed = discord.Embed(color=discord.Color.random())
            embed.add_field(name="KitShop - Здесь водятся киты 🐳",
                            value="Быстрая доставка, большой ассортимент, частые розыгрыши и дешевые цены - Все это описание нашего шопа 🛒 \nИспользуй бота снизу для просмотра ассортимента и покупки лучших китов 💸",
                            inline=False)
            embed.set_author(name="Kit shop",
                             icon_url="https://i.imgur.com/weDCY1n.png")
            embed.set_image(url="https://i.imgur.com/efOIYe4.png")
            msg = await message.channel.send(view=MyView(), embed=embed)
            CONFIG["menu_message_id"] = msg.id
            with open("config.json", "w", encoding="UTF-8") as file:
                json.dump(CONFIG, file)
            await message.delete()
        elif message.content.startswith('$adminPanel'):
            embed = discord.Embed(color=discord.Color.random())
            embed.add_field(name="Админ панель",
                            value="Одмэн",
                            inline=False)
            msg = await message.channel.send(view=AdminPanelView(), embed=embed)
            CONFIG["admin_panel_message_id"] = msg.id
            with open("config.json", "w", encoding="UTF-8") as file:
                json.dump(CONFIG, file)
            await message.delete()


async def setup_hook():
    client.add_view(MyView(), message_id=CONFIG["menu_message_id"])
    client.add_view(AdminPanelView(), message_id=CONFIG["admin_panel_message_id"])


client.setup_hook = setup_hook

with open(".token") as token_file:
    token = token_file.read()
client.run(token)
