from esi.clients import EsiClientProvider


class CorpToolsESIClient(EsiClientProvider):

    # TODO create provider dummy classes for use here to not have to deal with ORM model bullshit and maybe be more async?.

    @staticmethod
    def chunk_ids(lo, n=750):
        for i in range(0, len(lo), n):
            yield lo[i : i + n]


esi = CorpToolsESIClient()
