class MachineFilter {
    constructor() {
        this.query = {};
    }

    withStatus(statusArray) {
        if (Array.isArray(statusArray) && statusArray.length > 0) {
            this.query.status = { $in: statusArray };
        }
        return this;
    }

    withCreatedFrom(date) {
        if (date) {
            this.query.createdAt = this.query.createdAt || {};
            this.query.createdAt.$gte = new Date(date);
        }
        return this;
    }

    withCreatedTo(date) {
        if (date) {
            this.query.createdAt = this.query.createdAt || {};
            this.query.createdAt.$lte = new Date(date);
        }
        return this;
    }

    withQuery(search) {
        if (search && search.trim() !== "") {
            this.query.$or = [
                { name: { $regex: search, $options: "i" } },
                { description: { $regex: search, $options: "i" } }
            ];
        }
        return this;
    }

    build() {
        return this.query;
    }
}

module.exports = MachineFilter;
