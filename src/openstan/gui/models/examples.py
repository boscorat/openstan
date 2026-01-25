from PyQt6.QtGui import QStandardItem, QStandardItemModel


class TreeModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels(["Name", "Description", "Value"])

        # Add some data
        root_item = QStandardItem("States")

        # Add states as children
        california = QStandardItem("California")
        california_pop = QStandardItem("39.5M")
        california_desc = QStandardItem("The Golden State")
        root_item.appendRow([california, california_desc, california_pop])

        texas = QStandardItem("Texas")
        texas_pop = QStandardItem("29.0M")
        texas_desc = QStandardItem("The Lone Star State")
        root_item.appendRow([texas, texas_desc, texas_pop])

        # Add cities to California
        ca_cities = [("Los Angeles", "The City of Angels", "3.9M"), ("San Francisco", "The Golden Gate City", "0.8M")]
        for city, desc, pop in ca_cities:
            city_item = QStandardItem(city)
            desc_item = QStandardItem(desc)
            pop_item = QStandardItem(pop)
            california.appendRow([city_item, desc_item, pop_item])
        # Add cities to Texas
        tx_cities = [("Houston", "The Space City", "2.3M"), ("Austin", "The Live Music Capital", "0.9M")]
        for city, desc, pop in tx_cities:
            city_item = QStandardItem(city)
            desc_item = QStandardItem(desc)
            pop_item = QStandardItem(pop)
            texas.appendRow([city_item, desc_item, pop_item])

        # Add the root item to the model
        self.appendRow(root_item)
