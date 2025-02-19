import { SharedArray } from 'k6/data';


export function readUsersFromFile(filePath = "../../../data/accounts.json") {
    const users = new SharedArray('Users accounts', function () {
        const accounts = JSON.parse(open(filePath));
        let data = [];
        for (let i = 0; i < Object.keys(accounts).length; i++) {
            data[i] = accounts[i];
        }
        return data;
    });

    return users
}