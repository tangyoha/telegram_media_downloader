var request = (url, type = 'get' | 'post', data) => {
    const $ = layui.$

    return new Promise((resolve, reject) => {
        $.ajax({
            url,
            type,
            data,
            dataType: 'json',
            timeout: 60 * 1000,
            contentType: 'application/x-www-form-urlencoded',
            success: (res) => {
                resolve(res)
            },
            error: (err) => {
                reject(err)
            }
        })
    })
}