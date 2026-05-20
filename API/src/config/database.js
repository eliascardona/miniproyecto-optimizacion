const { MongoClient, ServerApiVersion } = require("mongodb");

const uri = process.env.CURI;

let client;
let db;

async function connectDB() {
    if (db) return db;

    client = new MongoClient(uri, {
        serverApi: {
            version: ServerApiVersion.v1,
            strict: true,
            deprecationErrors: true,
        },
        tlsInsecure: true,
    });

    await client.connect();
    db = client.db(process.env.DB || "machines");
    console.log("✅ MongoDB connected:", db.databaseName);
    return db;
}

function getDB() {
    if (!db) throw new Error("DB not initialized. Call connectDB first.");
    return db;
}

async function disconnectDB() {
    if (client) {
        await client.close();
        console.log("❎ MongoDB disconnected");
    }
}

module.exports = { connectDB, getDB, disconnectDB };
