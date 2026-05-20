function formatPaginationOptions({
    page,
    size,
    sort,
    direction
}) {
    return {
        page: parseInt(page),
        size: parseInt(size),
        sort,
        direction
    }
}

module.exports = { formatPaginationOptions }
