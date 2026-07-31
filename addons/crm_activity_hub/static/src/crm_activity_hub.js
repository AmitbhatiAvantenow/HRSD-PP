/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { FileModel } from "@web/core/file_viewer/file_model";
import { download } from "@web/core/network/download";
import { _t } from "@web/core/l10n/translation";

const FEED_PAGE_SIZE = 15;
const SEARCH_DEBOUNCE_MS = 300;

function formatFileSize(bytes) {
    if (!bytes) {
        return "0 B";
    }
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let i = 0;
    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        i++;
    }
    return (i === 0 ? size : size.toFixed(1)) + " " + units[i];
}

function dayLabel(dateStr, today, yesterday) {
    if (!dateStr) {
        return "";
    }
    const day = dateStr.slice(0, 10);
    if (day === today) {
        return "Today";
    }
    if (day === yesterday) {
        return "Yesterday";
    }
    return luxon.DateTime.fromSQL(dateStr).toFormat("dd LLL yyyy");
}

function groupByDay(entries) {
    const now = luxon.DateTime.now();
    const today = now.toFormat("yyyy-MM-dd");
    const yesterday = now.minus({ days: 1 }).toFormat("yyyy-MM-dd");
    const groups = [];
    const byLabel = {};
    for (const entry of entries) {
        const label = dayLabel(entry.date, today, yesterday);
        if (!byLabel[label]) {
            byLabel[label] = { label, items: [] };
            groups.push(byLabel[label]);
        }
        byLabel[label].items.push(entry);
    }
    return groups;
}

export class CrmActivityHub extends Component {
    static template = "crm_activity_hub.CrmActivityHub";
    static components = { Chatter };
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.fileViewer = useFileViewer();
        this.state = useState({
            activeTab: "activity",
            feed: [],
            feedHasMore: true,
            feedLoading: false,
            feedSearch: "",
            documents: [],
            documentsLoaded: false,
            documentsSearch: "",
            timeline: [],
            timelineLoaded: false,
            timelineSearch: "",
            previewLoadingIds: [],
        });
        this.searchTimeout = null;
        onWillStart(() => this.loadFeed());
    }

    get resId() {
        return this.props.record.resId;
    }

    formatFileSize(bytes) {
        return formatFileSize(bytes);
    }

    get feedGroups() {
        return groupByDay(this.state.feed);
    }

    get filteredDocuments() {
        const needle = this.state.documentsSearch.trim().toLowerCase();
        if (!needle) {
            return this.state.documents;
        }
        return this.state.documents.filter((doc) => doc.name.toLowerCase().includes(needle));
    }

    get filteredTimeline() {
        const needle = this.state.timelineSearch.trim().toLowerCase();
        if (!needle) {
            return this.state.timeline;
        }
        return this.state.timeline.filter(
            (entry) => (entry.title + " " + entry.subtitle).toLowerCase().includes(needle)
        );
    }

    onDocumentsSearchInput(ev) {
        this.state.documentsSearch = ev.target.value;
    }

    onTimelineSearchInput(ev) {
        this.state.timelineSearch = ev.target.value;
    }

    async selectTab(tab) {
        this.state.activeTab = tab;
        if (tab === "documents" && !this.state.documentsLoaded) {
            await this.loadDocuments();
        } else if (tab === "timeline" && !this.state.timelineLoaded) {
            await this.loadTimeline();
        }
    }

    onSearchInput(ev) {
        this.state.feedSearch = ev.target.value;
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => this.loadFeed(true), SEARCH_DEBOUNCE_MS);
    }

    async loadFeed(reset = false) {
        if (!this.resId) {
            return;
        }
        if (reset) {
            this.state.feed = [];
            this.state.feedHasMore = true;
        }
        this.state.feedLoading = true;
        try {
            const result = await this.orm.call("crm.lead", "get_activity_hub_feed", [this.resId], {
                offset: this.state.feed.length,
                limit: FEED_PAGE_SIZE,
                search: this.state.feedSearch,
            });
            this.state.feed.push(...result.items);
            this.state.feedHasMore = result.has_more;
        } finally {
            this.state.feedLoading = false;
        }
    }

    /**
     * Builds a lightweight file model (same interface the standard chatter
     * uses) so we can reuse Odoo's own popup viewer / download plumbing.
     */
    toFileModel(attachment) {
        const file = new FileModel();
        Object.assign(file, {
            id: attachment.id,
            name: attachment.name,
            mimetype: attachment.mimetype,
            type: "binary",
            uploading: false,
        });
        return file;
    }

    isPreviewLoading(attachment) {
        return this.state.previewLoadingIds.includes(attachment.id);
    }

    async onClickPreview(attachment) {
        const file = this.toFileModel(attachment);
        if (file.isViewable) {
            this.fileViewer.open(file, [file]);
            return;
        }
        if (this.isPreviewLoading(attachment)) {
            return;
        }
        this.state.previewLoadingIds.push(attachment.id);
        try {
            const pdfAttachmentId = await this.orm.call(
                "ir.attachment", "get_preview_pdf_attachment_id", [attachment.id]
            );
            if (pdfAttachmentId) {
                const pdfFile = this.toFileModel({
                    id: pdfAttachmentId,
                    name: attachment.name,
                    mimetype: "application/pdf",
                });
                this.fileViewer.open(pdfFile, [pdfFile]);
                return;
            }
            this.notification.add(
                _t("No inline preview available for this file — downloading instead."),
                { type: "info" }
            );
            this.onClickDownload(attachment);
        } finally {
            const idx = this.state.previewLoadingIds.indexOf(attachment.id);
            if (idx !== -1) {
                this.state.previewLoadingIds.splice(idx, 1);
            }
        }
    }

    onClickDownload(attachment) {
        const file = this.toFileModel(attachment);
        download({ data: {}, url: file.downloadUrl });
    }

    async loadDocuments() {
        if (!this.resId) {
            return;
        }
        this.state.documents = await this.orm.call("crm.lead", "get_activity_hub_documents", [this.resId]);
        this.state.documentsLoaded = true;
    }

    async loadTimeline() {
        if (!this.resId) {
            return;
        }
        this.state.timeline = await this.orm.call("crm.lead", "get_activity_hub_timeline", [this.resId]);
        this.state.timelineLoaded = true;
    }
}

registry.category("view_widgets").add("crm_activity_hub", { component: CrmActivityHub });
