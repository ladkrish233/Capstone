class PostgresSpillStore:
    def __init__(self,pool):
        self.pool=pool
        
    async def write(self,key:str,data:bytes)->str:
        await self.pool.execute(
            """insert into friend_tool_spills (handle, data) values ($1, $2)
            on conflict (handle) do update set data = excluded.data""",
        key, data,
    )
        return key
        
    async def read(self,handle:str)->bytes:
        row=await self.pool.fetchrow(
            "select data from friend_tool_spills where handle = $1", handle
        )
        if row is None:
            raise FileNotFoundError(handle)
        return bytes(row(['data']))