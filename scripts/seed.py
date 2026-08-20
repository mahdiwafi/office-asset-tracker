"""Seed the local database with demo categories and assets.

Safe to re-run: exits early when assets already exist.

Run: uv run python -m scripts.seed
"""

import asyncio

import sqlalchemy as sa

from app.db import async_session_factory
from app.models import Asset, AssetCondition, AssetStatus, Category

CATEGORIES: list[tuple[str, str]] = [
	('Laptop', 'Portable computers'),
	('Monitor', 'External displays'),
	('Phone', 'Mobile devices'),
	('Peripheral', 'Keyboards, mice, docks'),
	('Other', 'Miscellaneous IT equipment'),
]

ASSETS: list[tuple[str, str, str, str, str, str]] = [
	# (inventory_tag, name, serial, category, status, condition)
	('IT-0001', 'ThinkPad X1 Carbon', 'PF1ABC123', 'Laptop', 'available', 'good'),
	('IT-0002', 'ThinkPad T14', 'PF1ABC124', 'Laptop', 'available', 'good'),
	('IT-0003', 'Dell U2723QE 27in', 'DELL27123', 'Monitor', 'available', 'new'),
	('IT-0004', 'iPhone 15', 'F2LLHX4Q', 'Phone', 'loaned', 'good'),
	('IT-0005', 'Magic Mouse', 'MM2024001', 'Peripheral', 'available', 'fair'),
	(
		'IT-0006',
		'Docking station USB-C',
		'DOCK10123',
		'Peripheral',
		'maintenance',
		'poor',
	),
	('IT-0007', 'iPad Pro 11', 'DLXWY1KP', 'Phone', 'damaged', 'fair'),
]


async def main() -> None:
	async with async_session_factory() as session:
		existing = await session.scalar(sa.select(sa.func.count()).select_from(Asset))
		if existing:
			print(f'{existing} assets already present — nothing to do.')
			return
		categories: dict[str, Category] = {}
		for name, description in CATEGORIES:
			category = Category(name=name, description=description)
			session.add(category)
			categories[name] = category
		# Flush so the categories have ids before the assets reference them.
		await session.flush()
		for tag, name, serial, category_name, status, condition in ASSETS:
			session.add(
				Asset(
					inventory_tag=tag,
					name=name,
					serial=serial,
					category_id=categories[category_name].id,
					status=AssetStatus[status],
					condition=AssetCondition[condition],
				)
			)
		await session.commit()
		print(f'Seeded {len(CATEGORIES)} categories and {len(ASSETS)} assets.')


if __name__ == '__main__':
	asyncio.run(main())
