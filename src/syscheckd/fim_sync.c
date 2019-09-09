/**
 * @file fim_sync.c
 * @author Vikman Fernandez-Castro (victor@wazuh.com)
 * @brief Definition of FIM data synchronization library
 * @version 0.1
 * @date 2019-08-28
 *
 * @copyright Copyright (c) 2019 Wazuh, Inc.
 */

/*
 * This program is a free software; you can redistribute it
 * and/or modify it under the terms of the GNU General Public
 * License (version 2) as published by the FSF - Free Software
 * Foundation.
 */

#include <shared.h>
#include <openssl/evp.h>
#include "syscheck.h"
#include "integrity_op.h"

static long fim_sync_cur_id;

char * dbsync_check_msg(const char * component, long id, const char * start, const char * top, const char * tail, const char * checksum) {
    cJSON * root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "component", component);

    if (checksum == NULL) {
        cJSON_AddStringToObject(root, "type", "clear");
    } else {
        cJSON_AddStringToObject(root, "type", "check");

        cJSON * data = cJSON_CreateObject();
        cJSON_AddItemToObject(root, "data", data);

        cJSON_AddNumberToObject(data, "id", id);
        cJSON_AddStringToObject(data, "begin", start);
        cJSON_AddStringToObject(data, "end", top);

        if (tail != NULL) {
            cJSON_AddStringToObject(data, "tail", tail);
        }

        cJSON_AddStringToObject(data, "checksum", checksum);
    }

    char * payload = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return payload;
}

/**
 * @brief Create file attribute set JSON from a FIM entry structure
 *
 * Form:
 * {
 *   type:        file|registry
 *   size:        number
 *   perm:        number
 *   user_name:   string
 *   group_name:  string
 *   uid:         string
 *   gid:         string
 *   inode:       number
 *   mtime:       number
 *   hash_md5:    string
 *   hash_sha1:   string
 *   hash_sha256: string
 *   checksum:    string
 * }
 *
 * @param data Pointer to a FIM entry structure.
 * @pre data is mutex-blocked.
 * @return Pointer to cJSON structure.
 */

cJSON * fim_attributes_json(const fim_entry_data * data) {
    cJSON * attributes = cJSON_CreateObject();

    // TODO: Read structure.
    cJSON_AddStringToObject(attributes, "type", "file");

    if (data->size) {
        cJSON_AddNumberToObject(attributes, "size", data->size);
    }

    if (data->perm) {
        cJSON_AddNumberToObject(attributes, "perm", data->perm);
    }

    if (data->uid) {
        char text[64];
        snprintf(text, sizeof(text), "%u", data->uid);
        cJSON_AddStringToObject(attributes, "uid", text);
    }

    if (data->gid) {
        char text[64];
        snprintf(text, sizeof(text), "%u", data->gid);
        cJSON_AddStringToObject(attributes, "gid", text);
    }

    if (data->user_name) {
        cJSON_AddStringToObject(attributes, "user_name", data->user_name);
    }

    if (data->group_name) {
        cJSON_AddStringToObject(attributes, "group_name", data->group_name);
    }

    if (data->inode) {
        cJSON_AddNumberToObject(attributes, "inode", data->inode);
    }

    if (data->mtime) {
        cJSON_AddNumberToObject(attributes, "mtime", data->mtime);
    }

    if (data->hash_md5) {
        cJSON_AddStringToObject(attributes, "hash_md5", data->hash_md5);
    }

    if (data->hash_sha1) {
        cJSON_AddStringToObject(attributes, "hash_sha1", data->hash_sha1);
    }

    if (data->hash_sha256) {
        cJSON_AddStringToObject(attributes, "hash_sha256", data->hash_sha256);
    }

    if (data->checksum) {
        cJSON_AddStringToObject(attributes, "checksum", data->checksum);
    }

    return attributes;
}

/**
 * @brief Create file entry JSON from a FIM entry structure
 *
 * Form:
 * {
 *   path:          string
 *   timestamp:     number
 *   attributes: {
 *     type:        file|registry
 *     size:        number
 *     perm:        number
 *     user_name:   string
 *     group_name:  string
 *     uid:         string
 *     gid:         string
 *     inode:       number
 *     mtime:       number
 *     hash_md5:    string
 *     hash_sha1:   string
 *     hash_sha256: string
 *     checksum:    string
 *   }
 * }
 *
 * @param path Pointer to file path string.
 * @param data Pointer to a FIM entry structure.
 * @pre data is mutex-blocked.
 * @return Pointer to cJSON structure.
 */

cJSON * fim_entry_json(const char * path, fim_entry_data * data) {
    assert(data);
    assert(path);

    cJSON * root = cJSON_CreateObject();

    cJSON_AddStringToObject(root, "path", path);
    cJSON_AddNumberToObject(root, "timestamp", data->scanned);

    cJSON * attributes = fim_attributes_json(data);
    cJSON_AddItemToObject(root, "attributes", attributes);

    return root;
}

/**
 * @brief Create a data synchronization save message
 *
 * @param component Name of the component.
 * @param data Synchronization data.
 * @post data is destroyed.
 * @return Pointer to dynamically allocated string.
 */
char * dbsync_file_msg(const char * component, cJSON * data) {
    cJSON * root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "component", component);
    cJSON_AddStringToObject(root, "type", "save");
    cJSON_AddItemToObject(root, "data", data);

    char * msg = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return msg;
}

void fim_sync_checksum() {
    char ** keys;
    int i;
    EVP_MD_CTX * ctx = EVP_MD_CTX_create();
    EVP_DigestInit(ctx, EVP_sha1());

    w_mutex_lock(&syscheck.fim_entry_mutex);

    {
        keys = rbtree_keys(syscheck.fim_entry);

        for (i = 0; keys[i]; i++) {
            fim_entry_data * data = rbtree_get(syscheck.fim_entry, keys[i]);
            assert(data);
            EVP_DigestUpdate(ctx, data->checksum, strlen(data->checksum));
        }
    }

    w_mutex_unlock(&syscheck.fim_entry_mutex);
    fim_sync_cur_id = time(NULL);

    if (i > 0) {
        unsigned char digest[EVP_MAX_MD_SIZE];
        unsigned int digest_size;
        os_sha1 hexdigest;

        EVP_DigestFinal_ex(ctx, digest, &digest_size);
        OS_SHA1_Hexdigest(digest, hexdigest);

        char * plain = dbsync_check_msg("syscheck", fim_sync_cur_id, keys[0], keys[i - 1], NULL, hexdigest);
        fim_send_sync_msg(plain);
        free(plain);
    } else {
        char * plain = dbsync_check_msg("syscheck", fim_sync_cur_id, NULL, NULL, NULL, NULL);
        fim_send_sync_msg(plain);
        free(plain);
    }

    EVP_MD_CTX_destroy(ctx);
    free_strarray(keys);
}

void fim_sync_checksum_split(const char * start, const char * top) {
    cJSON * entry_data = NULL;
    char ** keys;
    int n;
    int m;
    EVP_MD_CTX * ctx_left = EVP_MD_CTX_create();
    EVP_MD_CTX * ctx_right = EVP_MD_CTX_create();

    EVP_DigestInit(ctx_left, EVP_sha1());
    EVP_DigestInit(ctx_right, EVP_sha1());

    w_mutex_lock(&syscheck.fim_entry_mutex);

    {
        keys = rbtree_range(syscheck.fim_entry, start, top);
        for (n = 0; keys[n]; n++);

        switch (n) {
        case 0:
            break;

        case 1:
            // Unary list: send the file state
            entry_data = fim_entry_json(keys[0], (fim_entry_data *) rbtree_get(syscheck.fim_entry, keys[0]));
            break;

        default:
            // Other case: split the list
            m = n / 2;

            for (int i = 0; i < m; i++) {
                fim_entry_data * data = rbtree_get(syscheck.fim_entry, keys[i]);
                assert(data);
                EVP_DigestUpdate(ctx_left, data->checksum, strlen(data->checksum));
            }

            for (int i = m; i < n; i++) {
                fim_entry_data * data = rbtree_get(syscheck.fim_entry, keys[i]);
                assert(data);
                EVP_DigestUpdate(ctx_right, data->checksum, strlen(data->checksum));
            }
        }
    }

    w_mutex_lock(&syscheck.fim_entry_mutex);

    if (n > 0) {
        if (entry_data == NULL) {
            unsigned char digest[EVP_MAX_MD_SIZE];
            unsigned int digest_size;
            os_sha1 hexdigest;

            EVP_DigestFinal_ex(ctx_left, digest, &digest_size);
            OS_SHA1_Hexdigest(digest, hexdigest);
            char * plain = dbsync_check_msg("syscheck", 1, keys[0], keys[m - 1], keys[m], hexdigest);
            fim_send_sync_msg(plain);
            free(plain);

            EVP_DigestFinal_ex(ctx_right, digest, &digest_size);
            OS_SHA1_Hexdigest(digest, hexdigest);
            plain = dbsync_check_msg("syscheck", 1, keys[m], keys[n - 1], "", hexdigest);
            fim_send_sync_msg(plain);
            free(plain);
        } else {
            mdebug2(FIM_DBSYNC_SEND_FILE, cJSON_GetStringValue(cJSON_GetObjectItem(entry_data, "file")));
            char * plain = dbsync_file_msg("syscheck", entry_data);
            fim_send_sync_msg(plain);
            free(plain);
        }
    }

    free_strarray(keys);
    EVP_MD_CTX_destroy(ctx_left);
    EVP_MD_CTX_destroy(ctx_right);
}

void fim_sync_send_list(const char * start, const char * top) {
    w_mutex_lock(&syscheck.fim_entry_mutex);
    char ** keys = rbtree_range(syscheck.fim_entry, start, top);
    w_mutex_unlock(&syscheck.fim_entry_mutex);

    for (int i = 0; keys[i]; i++) {
        w_mutex_lock(&syscheck.fim_entry_mutex);
        fim_entry_data * data = rbtree_get(syscheck.fim_entry, keys[i]);

        if (data == NULL) {
            w_mutex_unlock(&syscheck.fim_entry_mutex);
            continue;
        }

        cJSON * entry_data = fim_entry_json(keys[i], data);
        w_mutex_unlock(&syscheck.fim_entry_mutex);

        mdebug2(FIM_DBSYNC_SEND_FILE, keys[i]);

        char * plain = dbsync_file_msg("syscheck", entry_data);
        fim_send_sync_msg(plain);
        free(plain);
    }

    free_strarray(keys);
}

void fim_sync_dispatch(char * payload) {
    assert(payload != NULL);

    char * command = payload;
    char * json_arg = strchr(payload, ' ');

    if (json_arg == NULL) {
        mdebug1(FIM_DBSYNC_NO_ARGUMENT, payload);
        return;
    }

    *json_arg++ = '\0';
    cJSON * root = cJSON_Parse(json_arg);

    if (root == NULL) {
        mdebug1(FIM_DBSYNC_INVALID_ARGUMENT, json_arg);
        return;
    }

    cJSON * id = cJSON_GetObjectItem(root, "id");

    if (!cJSON_IsNumber(id)) {
        mdebug1(FIM_DBSYNC_INVALID_ARGUMENT, json_arg);
        goto end;
    }

    // Discard command if (data.id > global_id)
    // Decrease global ID if (data.id < global_id)

    if (id->valuedouble < fim_sync_cur_id) {
        fim_sync_cur_id = id->valuedouble;
        mdebug1(FIM_DBSYNC_DEC_ID, fim_sync_cur_id);
    } else if (id->valuedouble < fim_sync_cur_id) {
        mdebug1(FIM_DBSYNC_DROP_MESSAGE, (long)id->valuedouble, fim_sync_cur_id);
        return;
    }

    char * begin = cJSON_GetStringValue(cJSON_GetObjectItem(root, "begin"));
    char * end = cJSON_GetStringValue(cJSON_GetObjectItem(root, "end"));

    if (begin == NULL || end == NULL) {
        mdebug1(FIM_DBSYNC_INVALID_ARGUMENT, end);
        goto end;
    }

    if (strcmp(command, "checksum_fail") == 0) {
        fim_sync_checksum_split(begin, end);
    } else if (strcmp(command, "no_data") == 0) {
        fim_sync_send_list(begin, end);
    } else {
        mdebug1(FIM_DBSYNC_UNKNOWN_CMD, command);
    }

end:
    cJSON_Delete(root);
}
