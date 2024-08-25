import sqlite3


class DatabaseManager:
    def __init__(self):
        self.db_connection = sqlite3.connect('mainDatabase.db')
        cursor = self.db_connection.cursor()
        cursor.executescript('''
        CREATE TABLE IF NOT EXISTS Orders (
        id INTEGER PRIMARY KEY,
        discord_id INTEGER NOT NULL,
        minecraft_username TEXT(16),
        order_message_id INTEGER,
        closed BOOLEAN NOT NULL DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS Carts (
        discord_id INTEGER PRIMARY KEY,
        cart TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS Items (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        price INTEGER NOT NULL
        );
        ''')
        cursor.close()
        self.db_connection.commit()

    def parse_cart(self, cart:str)->list:
        if ',' in cart:
            return list(map(lambda item: list(map(int, item.split())), cart.split(',')))
        return [list(map(int, cart.split()))]

    def execute_sql(self, query, args):
        cursor = self.db_connection.cursor()
        cursor.execute(query, args)
        self.db_connection.commit()
        cursor.close()

    def update_or_create_cart(self, discord_user_id:int, item_to_add:list):
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT cart FROM Carts WHERE discord_id = ?', (discord_user_id,))
        ret = cursor.fetchone()
        if ret is None:
            cursor.execute('INSERT INTO Carts (discord_id, cart) VALUES (?, ?)',
                           (discord_user_id, f"{item_to_add[0]} {item_to_add[1]}"))
        else:
            cart = ret[0]
            if ',' in cart:
                new_cart = []
                flag = True
                cart = list(map(lambda item: item.split(), cart.split(',')))
                for item in cart:
                    if item[0] != str(item_to_add[0]):
                        new_cart.append(' '.join(item))
                        continue
                    if item_to_add[1] == 0:
                        continue
                    flag = False
                    new_cart.append(f"{item_to_add[0]} {item_to_add[1]}")
                if flag and item_to_add[1] != 0:
                    new_cart.append(f"{item_to_add[0]} {item_to_add[1]}")
                cart = ','.join(new_cart)
            else:
                item = cart.split()
                if item[0] != str(item_to_add[0]):
                    cart += f",{item_to_add[0]} {item_to_add[1]}"
                elif item_to_add[1] == 0:
                    cursor.execute('UPDATE Carts SET cart = '' WHERE discord_id = ?', (discord_user_id,))
                    self.db_connection.commit()
                    cursor.close()
                    return
                else:
                    cart = f"{item_to_add[0]} {item_to_add[1]}"
            cursor.execute('UPDATE Carts SET cart = ? WHERE discord_id = ?', (cart, discord_user_id,))
        self.db_connection.commit()

        cursor.close()

    def get_cart(self, discord_user_id:int)->list:
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT cart FROM Carts WHERE discord_id = ?', (discord_user_id,))
        ret = cursor.fetchone()
        cursor.close()

        if ret is None:
            return []
        return self.parse_cart(ret[0])

    def clear_cart(self, discord_user_id:int):
        self.execute_sql('DELETE FROM Carts WHERE discord_id = ?', (discord_user_id,))

    def create_order(self, discord_user_id:int)->int:
        cursor = self.db_connection.cursor()
        cursor.execute(
            'SELECT id FROM Orders WHERE discord_id = ? AND closed = 0',
            (discord_user_id,))
        ret = cursor.fetchone()
        if ret is None:
            cursor.execute('INSERT OR IGNORE INTO Orders (discord_id) VALUES (?)',
                           (discord_user_id,))
            self.db_connection.commit()
            ret = cursor.lastrowid
        else:
            ret = int(ret[0])
        cursor.close()
        return ret

    def get_order(self, order_id:int) -> list:
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT discord_id, minecraft_username, order_message_id FROM Orders WHERE id = ? AND closed = 0', (order_id,))
        ret = cursor.fetchone()
        cursor.close()
        if ret is None:
            return []
        discord_id, minecraft_username, order_message_id = ret
        return [discord_id, minecraft_username, order_message_id]

    def get_order_by_discord_id(self, discord_user_id:int) -> list:
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT id, minecraft_username, order_message_id FROM Orders WHERE discord_id = ? AND closed = 0', (discord_user_id,))
        ret = cursor.fetchone()
        cursor.close()
        return ret

    def close_order(self, order_id:int):
        self.execute_sql('UPDATE Orders SET closed = 1 WHERE id = ? AND closed = 0', (order_id,))

    def delete_order(self, order_id:int):
        self.execute_sql('DELETE FROM Orders WHERE id = ? AND closed = 0', (order_id,))

    def set_order_minecraft_nickname(self, order_id:int, minecraft_username:str):
        self.execute_sql('UPDATE Orders SET minecraft_username = ? WHERE id = ?', (minecraft_username, order_id))

    def set_order_channel_id(self, order_id:int, order_message_id:int):
        self.execute_sql('UPDATE Orders SET order_message_id = ? WHERE id = ?', (order_message_id, order_id))

    def get_items(self) -> dict:
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT id, name, url, price FROM Items', ())
        ret = cursor.fetchall()
        cursor.close()
        if ret is None:
            return {}

        items = {}
        for item in ret:
            items[item[0]] = [item[1], item[2], int(item[3])]
        return items

    def set_items_name(self, item_id:int, new_name:str):
        self.execute_sql('UPDATE Items SET name = ? WHERE id = ?', (new_name, item_id))

    def set_items_url(self, item_id:int, new_url:str):
        self.execute_sql('UPDATE Items SET url = ? WHERE id = ?', (new_url, item_id))

    def set_items_price(self, item_id:int, new_price:int):
        self.execute_sql('UPDATE Items SET price = ? WHERE id = ?', (new_price, item_id))

    def remove_item(self, item_id:int):
        self.execute_sql('DELETE FROM Items WHERE id = ?', (item_id,))

        self.remove_item_from_carts(item_id)

    def remove_item_from_carts(self, item_id:int):
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT cart, discord_id FROM Carts', ())
        ret = cursor.fetchall()
        cursor.close()
        if ret is None:
            return

        for cart, discord_id in ret:
            cart = self.parse_cart(cart)
            for i in range(len(cart)):
                if cart[i][0] == item_id:
                    self.update_or_create_cart(discord_id, [item_id, 0])
                    break

    def add_item(self, name:str, image_url:str, price:int) -> int:
        cursor = self.db_connection.cursor()
        cursor.execute('INSERT INTO Items (name, url, price) VALUES (?, ?, ?)', (name, image_url, price))
        self.db_connection.commit()
        cursor.close()
        return cursor.lastrowid


if __name__ == "__main__":
    orders_manager = DatabaseManager()
    order_id = orders_manager.create_order(42523542354)
    print(order_id)
    print(orders_manager.get_order(order_id))
    orders_manager.set_order_minecraft_nickname(order_id, "lolol")
    orders_manager.set_order_channel_id(order_id, 174589175932)
    print(orders_manager.get_order(order_id))

    order_id = orders_manager.create_order(42523542354)
    print(order_id)
    orders_manager.close_order(order_id)