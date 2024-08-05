import frappe
from frappe.model.document import Document
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


class DatafieldSeries(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings = frappe.get_single("TV Data Settings")
        self.use_influxdb = settings.use_influxdb

    def db_insert(self, *args, **kwargs):
        if self.use_influxdb:
            self.influxdb_insert()
        else:
            super().db_insert(*args, **kwargs)

    def load_from_db(self):
        if self.use_influxdb:
            self.influxdb_load()
        else:
            super().load_from_db()

    def db_update(self, *args, **kwargs):
        if self.use_influxdb:
            self.influxdb_update()
        else:
            super().db_update(*args, **kwargs)

    def delete(self):
        if self.use_influxdb:
            self.influxdb_delete()
        else:
            super().delete()

    @staticmethod
    def get_list(args):
        settings = frappe.get_single("TV Data Settings")
        if settings.use_influxdb:
            return DatafieldSeriesBase.influxdb_get_list(args)
        else:
            return frappe.get_all(
                "Datafield Series", filters=args.get("filters", {}), fields=["*"]
            )

    @staticmethod
    def get_count(args):
        settings = frappe.get_single("TV Data Settings")
        if settings.use_influxdb:
            return len(DatafieldSeriesBase.influxdb_get_list(args))
        else:
            return frappe.db.count("Datafield Series", filters=args.get("filters", {}))

    @staticmethod
    def get_stats(args):
        settings = frappe.get_single("TV Data Settings")
        if settings.use_influxdb:
            # Implement InfluxDB-specific stats calculation
            return {}
        else:
            # Implement Frappe DB-specific stats calculation
            return {}

    def influxdb_insert(self):
        self.write_to_influxdb()

    def influxdb_load(self):
        # Implement loading data from InfluxDB
        pass

    def influxdb_update(self):
        self.write_to_influxdb()

    def influxdb_delete(self):
        self.delete_from_influxdb()

    @staticmethod
    def influxdb_get_list(args):
        return get_series_data(args.get("filters", {}))

    def write_to_influxdb(self):
        settings = frappe.get_single("TV Data Settings")
        client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.get_password("influxdb_token"),
            org=settings.influxdb_org,
        )
        write_api = client.write_api(write_options=SYNCHRONOUS)

        point = (
            Point("datafield_series")
            .tag("datafield", self.parent)
            .tag("key", frappe.get_value("Datafield", self.parent, "key"))
            .field("open", float(self.open))
            .field("high", float(self.high))
            .field("low", float(self.low))
            .field("close", float(self.close))
            .field("volume", int(self.volume))
            .time(self.date_string)
        )

        write_api.write(bucket=settings.influxdb_bucket, record=point)

    def delete_from_influxdb(self):
        settings = frappe.get_single("TV Data Settings")
        client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.get_password("influxdb_token"),
            org=settings.influxdb_org,
        )

        query = f"""
        from(bucket:"{settings.influxdb_bucket}")
          |> range(start: 0)
          |> filter(fn: (r) => r._measurement == "datafield_series")
          |> filter(fn: (r) => r.datafield == "{self.parent}")
          |> filter(fn: (r) => r._time == {self.date_string})
        """

        delete_api = client.delete_api()
        delete_api.delete(
            start=self.date_string, stop=self.date_string, predicate=query
        )


def get_series_data(filters):
    settings = frappe.get_single("TV Data Settings")
    client = InfluxDBClient(
        url=settings.influxdb_url,
        token=settings.get_password("influxdb_token"),
        org=settings.influxdb_org,
    )

    query = f"""
    from(bucket:"{settings.influxdb_bucket}")
      |> range(start: {filters.get('start_date', '0')}, stop: {filters.get('end_date', 'now()')})
      |> filter(fn: (r) => r._measurement == "datafield_series")
    """

    if "datafield" in filters:
        query += f'|> filter(fn: (r) => r.datafield == "{filters["datafield"]}")'

    result = client.query_api().query(query)

    series_data = []
    for table in result:
        for record in table.records:
            series_data.append(
                DatafieldSeriesBase(
                    date_string=record.get_time(),
                    open=record.values.get("open"),
                    high=record.values.get("high"),
                    low=record.values.get("low"),
                    close=record.values.get("close"),
                    volume=record.values.get("volume"),
                    parent=record.values.get("datafield"),
                )
            )

    return series_data
