from rest_framework.pagination import PageNumberPagination


class Paginacao(PageNumberPagination):
    """Paginação padrão (20), com ?page_size= opcional para telas que
    precisam de mais itens de uma vez (ex.: gráfico de despesas)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 500
