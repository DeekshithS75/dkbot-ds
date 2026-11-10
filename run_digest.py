import asyncio
import logging

from db_client import DatabaseClient
from digest_email import send_event_digest


async def main():
    database = DatabaseClient()
    await database.async_init()

    try:
        await send_event_digest(database)
    finally:
        database.pool.closeall()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
