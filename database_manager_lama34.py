import sqlite3


class DatabaseManager:
    def __init__(self):
        self.db_connection = sqlite3.connect('mainDatabase.db')
        cursor = self.db_connection.cursor()
        cursor.executescript('''
        CREATE TABLE IF NOT EXISTS Orders (
        id INTEGER PRIMARY KEY,
        discord_id INTEGER NOT NULL,
        order_message_id INTEGER,
        order_channel_id INTEGER,
        item_id INTEGER,
        closed BOOLEAN NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS Items (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT
        );
        ''')
        cursor.close()
        self.db_connection.commit()

    def execute_sql(self, query, args):
        cursor = self.db_connection.cursor()
        cursor.execute(query, args)
        self.db_connection.commit()
        cursor.close()

    def create_order(self, discord_user_id: int, item_id:int) -> list:
        cursor = self.db_connection.cursor()
        cursor.execute(
            'SELECT id, order_channel_id FROM Orders WHERE discord_id = ? AND item_id = ? AND closed = 0',
            (discord_user_id, item_id))
        ret = cursor.fetchone()
        if ret is None:
            cursor.execute('INSERT OR IGNORE INTO Orders (discord_id, item_id) VALUES (?, ?)',
                           (discord_user_id, item_id))
            self.db_connection.commit()
            ret = [cursor.lastrowid, None]
        else:
            ret = [int(ret[0]), ret[1]]
        cursor.close()
        return ret

    def get_order(self, order_id: int) -> list:
        cursor = self.db_connection.cursor()
        cursor.execute(
            'SELECT discord_id, order_channel_id, order_message_id FROM Orders WHERE id = ? AND closed = 0',
            (order_id,))
        ret = cursor.fetchone()
        cursor.close()
        if ret is None:
            return []
        discord_id, order_channel_id, order_message_id = ret
        return [discord_id, order_channel_id, order_message_id]

    def get_order_by_discord_id(self, discord_user_id: int, item_id: int) -> list:
        cursor = self.db_connection.cursor()
        cursor.execute(
            'SELECT id, order_message_id FROM Orders WHERE discord_id = ? AND item_id = ? AND closed = 0',
            (discord_user_id, item_id))
        ret = cursor.fetchone()
        cursor.close()
        return ret

    def close_order(self, order_id: int):
        self.execute_sql('UPDATE Orders SET closed = 1 WHERE id = ? AND closed = 0', (order_id,))

    def delete_order(self, order_id: int):
        self.execute_sql('DELETE FROM Orders WHERE id = ? AND closed = 0', (order_id,))

    def set_order_channel_and_message_id(self, order_id: int, order_channel_id: int, order_message_id: int):
        self.execute_sql('UPDATE Orders SET order_channel_id = ?, order_message_id = ? WHERE id = ?', (order_channel_id, order_message_id, order_id))

    def get_items(self) -> dict:
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT id, name, url, price, description FROM Items', ())
        ret = cursor.fetchall()
        cursor.close()
        if ret is None:
            return {}

        items = {}
        for item in ret:
            items[item[0]] = [item[1], item[2], int(item[3]), item[4]]
        return items

    def get_item_by_id(self, item_id: int):
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT name, url, price, description FROM Items WHERE id = ?', (item_id,))
        ret = cursor.fetchone()
        cursor.close()
        return ret

    def set_items_name(self, item_id: int, new_name: str):
        self.execute_sql('UPDATE Items SET name = ? WHERE id = ?', (new_name, item_id))

    def set_items_url(self, item_id: int, new_url: str):
        self.execute_sql('UPDATE Items SET url = ? WHERE id = ?', (new_url, item_id))

    def set_items_price(self, item_id: int, new_price: int):
        self.execute_sql('UPDATE Items SET price = ? WHERE id = ?', (new_price, item_id))

    def set_items_description(self, item_id: int, new_description: str):
        self.execute_sql('UPDATE Items SET description = ? WHERE id = ?', (new_description, item_id))

    def remove_item(self, item_id: int):
        self.execute_sql('DELETE FROM Items WHERE id = ?', (item_id,))

    def add_item(self, name: str, image_url: str, price: int, description: str) -> int:
        cursor = self.db_connection.cursor()
        cursor.execute('INSERT INTO Items (name, url, price, description) VALUES (?, ?, ?, ?)', (name, image_url, price, description))
        self.db_connection.commit()
        cursor.close()
        return cursor.lastrowid