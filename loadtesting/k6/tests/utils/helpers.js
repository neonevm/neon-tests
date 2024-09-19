export async function waiter({ func, args, value, retries = 10 }) {
    return smartWaiter({ func, args, check: (r) => r == value, retries: retries });
}

export async function smartWaiter({ func, args, check, retries = 10 }) {
    let result;
    let counter = 0;
    while (!check(result) && counter < retries) {
        await new Promise(r => setTimeout(r, 200));
        if (args != undefined)
            result = await func(...args);
        else {
            result = await func();
        }
        counter++;
    }
    return result;
}