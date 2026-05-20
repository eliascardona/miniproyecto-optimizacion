const { Pool } = require('pg')

const pool = new Pool({
    database: 'maquiladora',
    host: 'localhost',
    port: 5432,
    user: 'eliascardona',
    password: 'elias123',
})


module.exports = pool
