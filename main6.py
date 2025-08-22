import flet as ft
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import enhanced backend functions
from ID_BRAIN_SMART_ROUTING1 import (
    process_ticket_id_enhanced,
    get_enhanced_claude_answer,
    autonomous_action_system,
    process_ticket_attachments_enhanced,
    analyze_ticket_comprehensively,
    get_pending_status_summary,
    print_ticket_summary,
)
print("Successfully imported enhanced functions from A_BRAIN_SMART_ROUTING1.py")

# Determine the current directory for asset loading
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


# Global ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=2)

# Global variables
current_active_ticket_data = None
active_workflow_id = None
workflow_step_status = {}  # Track individual step completion

# Status map
status_map = {
    1: "New",
    2: "Open",
    3: "Pending",
    4: "Resolved",
    5: "Closed"
}

# SOP Categories and their stages
SOP_STAGES = {
    "motor_claim": {
        1: "Initial Assessment",
        2: "Document Verification", 
        3: "Survey Assignment",
        4: "Survey Report Review",
        5: "Claim Settlement",
        6: "Closure"
    },
    "health_claim": {
        1: "Pre-authorization Review",
        2: "Medical Document Verification",
        3: "Treatment Approval",
        4: "Bill Verification",
        5: "Settlement Processing",
        6: "Closure"
    },
    "policy_issuance": {
        1: "Application Review",
        2: "KYC Verification",
        3: "Medical Assessment",
        4: "Underwriting",
        5: "Policy Generation",
        6: "Dispatch"
    },
    "customer_service": {
        1: "Query Analysis",
        2: "Information Gathering",
        3: "Solution Implementation",
        4: "Customer Communication",
        5: "Follow-up",
        6: "Resolution"
    }
}


def main(page: ft.Page):
    global current_active_ticket_data, active_workflow_id, workflow_step_status

    # --- Page Setup ---
    page.title = WINDOW_TITLE
    page.window_width = 1300
    page.window_height = 900
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    if os.path.exists(FULL_ICON_PATH):
        page.window_icon = FULL_ICON_PATH

    # --- Constants for Styling ---
    PRIMARY_BG_COLOR = "#1A1A1A"
    SECONDARY_BG_COLOR = "#2A2A2A"
    TEXT_COLOR_PRIMARY = ft.Colors.WHITE
    TEXT_COLOR_ACCENT = "#ADD8E6"
    TEXT_FONT = "Segoe UI"
    DEFAULT_PADDING = 15

    # Action priority colors
    PRIORITY_COLORS = {
        'HIGH': ft.Colors.RED_ACCENT_400,
        'URGENT': ft.Colors.RED_ACCENT_700,
        'MEDIUM': ft.Colors.ORANGE_ACCENT_400,
        'LOW': ft.Colors.GREEN_ACCENT_400
    }

    # --- Helper Functions ---
    def show_message(message_text: str, error: bool = False):
        page.snack_bar = ft.SnackBar(
            ft.Text(message_text, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_ACCENT_700 if error else ft.Colors.GREEN_ACCENT_700,
            open=True
        )
        page.update()

    def create_info_card(
        title: str,
        icon_name: str,
        initial_content: str = "",
        expandable: bool = False,
        scrollable: bool = False
    ):
        content_text_ctrl = ft.Text(
            initial_content,
            font_family=TEXT_FONT,
            size=10,
            color=TEXT_COLOR_PRIMARY,
            text_align=ft.TextAlign.CENTER,
            expand=True,
            selectable=True,
            max_lines=None if expandable else 5
        )

        # Wrap text in scrollable column if needed
        if scrollable:
            content_widget = ft.Column(
                [content_text_ctrl],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                height=80
            )
        else:
            content_widget = content_text_ctrl

        card = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icon_name, size=36, color=TEXT_COLOR_ACCENT),
                    ft.Text(
                        title,
                        font_family=TEXT_FONT,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_COLOR_PRIMARY,
                        text_align=ft.TextAlign.CENTER
                    ),
                    content_widget,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.START,
                spacing=5,
                expand=True
            ),
            bgcolor=SECONDARY_BG_COLOR,
            padding=10,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE10)),
            width=180 if not expandable else None,
            height=160 if not expandable else None,
            expand=expandable
        )
        card.data = content_text_ctrl
        return card

    def determine_current_workflow_stage(ticket_data: dict) -> int:
        """Automatically determine the current workflow stage based on ticket data"""
        if not ticket_data:
            return 1
            
        # Get the SOP category
        sop_category = ticket_data.get('sop_category', '').lower()
        if sop_category not in SOP_STAGES:
            return 1
            
        # Get ticket status
        status = ticket_data.get('status', 1)
        
        # Determine stage based on various factors
        current_stage = 1
        
        # Check if documents are available
        has_attachments = bool(ticket_data.get('attachments'))
        
        # Check ticket content for keywords that indicate progress
        ticket_content = ticket_data.get('raw_ticket_content', '').lower()
        problem = ticket_data.get('Problem', '').lower()
        solution = ticket_data.get('Solution', '').lower()
        
        # Stage determination logic based on SOP category
        if sop_category == "motor_claim":
            if "survey" in ticket_content or "surveyor" in problem:
                current_stage = 3
            elif "settlement" in ticket_content or "approved" in solution:
                current_stage = 5
            elif has_attachments:
                current_stage = 2
            elif status >= 4:
                current_stage = 6
                
        elif sop_category == "health_claim":
            if "pre-auth" in ticket_content or "preauth" in ticket_content:
                current_stage = 1
            elif "treatment" in ticket_content or "approved" in solution:
                current_stage = 3
            elif "bill" in ticket_content or "invoice" in ticket_content:
                current_stage = 4
            elif "settlement" in ticket_content:
                current_stage = 5
            elif status >= 4:
                current_stage = 6
                
        elif sop_category == "policy_issuance":
            if "kyc" in ticket_content or "verification" in ticket_content:
                current_stage = 2
            elif "medical" in ticket_content:
                current_stage = 3
            elif "underwriting" in ticket_content or "approved" in solution:
                current_stage = 4
            elif "policy" in solution or "generated" in solution:
                current_stage = 5
            elif status >= 4:
                current_stage = 6
                
        elif sop_category == "customer_service":
            if "information" in ticket_content or "details" in ticket_content:
                current_stage = 2
            elif "implementing" in solution or "resolved" in solution:
                current_stage = 3
            elif "communicated" in solution or "informed" in solution:
                current_stage = 4
            elif "follow" in ticket_content:
                current_stage = 5
            elif status >= 4:
                current_stage = 6
        
        # Ensure stage is within valid range
        max_stages = len(SOP_STAGES.get(sop_category, {}))
        return min(current_stage, max_stages)

    def create_workflow_details_section(workflow_data: dict) -> ft.Container:
        """Create a detailed workflow progress section with automated tracking."""
        if not workflow_data:
            return ft.Container()

        sop_steps = workflow_data.get('sop_steps', [])
        ticket_id = workflow_data.get('ticket_id', '')
        
        # Automatically determine current stage
        current_stage = determine_current_workflow_stage(current_active_ticket_data)
        
        # Update step status automatically
        step_status_key = f"{ticket_id}_steps"
        if step_status_key not in workflow_step_status:
            workflow_step_status[step_status_key] = {}
            
        # Mark steps as completed up to current stage
        for i in range(min(current_stage, len(sop_steps))):
            step_key = f"step_{i}"
            workflow_step_status[step_status_key][step_key] = True

        # Create step indicators with checkboxes for manual tracking
        step_indicators = []
        completed_count = current_stage - 1

        for i, step in enumerate(sop_steps):
            step_key = f"step_{i}"
            is_completed = workflow_step_status[step_status_key].get(step_key, False)

            if is_completed:
                color = ft.Colors.GREEN_ACCENT_400
                icon = ft.Icons.CHECK_CIRCLE
            elif i == completed_count:
                color = ft.Colors.BLUE_ACCENT_400
                icon = ft.Icons.RADIO_BUTTON_CHECKED
            else:
                color = ft.Colors.GREY_600
                icon = ft.Icons.RADIO_BUTTON_UNCHECKED

            checkbox = ft.Checkbox(
                value=is_completed,
                on_change=lambda e, idx=i, key=step_key: update_step_completion(
                    step_status_key, key, e.control.value, workflow_data
                )
            )

            step_indicators.append(
                ft.Row(
                    [
                        checkbox,
                        ft.Icon(icon, size=16, color=color),
                        ft.Text(
                            f"{i+1}. {step}",
                            size=11,
                            color=color if is_completed or i == completed_count else ft.Colors.GREY_400,
                            weight=ft.FontWeight.BOLD if i == completed_count else None,
                            expand=True
                        ),
                    ],
                    spacing=5
                )
            )

        # Update workflow progress based on actual completion
        total_steps = len(sop_steps)
        actual_completed = 0
        if total_steps > 0:
            actual_completed = sum(1 for step_key in workflow_step_status[step_status_key].values() if step_key)
            progress_percentage = (actual_completed / total_steps) * 100
            workflow_progress.value = progress_percentage / 100
            
            current_step_name = sop_steps[min(current_stage-1, total_steps-1)] if current_stage <= total_steps else 'Complete'
            workflow_status_text.value = (
                f"Progress: {progress_percentage:.0f}% ({actual_completed}/{total_steps} steps) - "
                f"Current: {current_step_name}"
            )

            # Update progress bar color based on completion
            if progress_percentage >= 90:
                workflow_progress.color = ft.Colors.GREEN_ACCENT_400
            elif progress_percentage >= 50:
                workflow_progress.color = ft.Colors.ORANGE_ACCENT_400
            else:
                workflow_progress.color = ft.Colors.BLUE_ACCENT_400

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        ft.Text("SOP Progress", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                        ft.Container(expand=True),
                        ft.Text(f"{actual_completed}/{total_steps}", size=12, color=ft.Colors.GREY_400)
                    ]),
                    ft.Divider(height=10, color=ft.Colors.WHITE10),
                    ft.Column(step_indicators, spacing=3),
                ],
                spacing=10
            ),
            padding=15,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            border_radius=8,
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE10))
        )

    def update_step_completion(status_key: str, step_key: str, is_completed: bool, workflow_data: dict):
        """Update step completion status and recalculate progress"""
        workflow_step_status[status_key][step_key] = is_completed

        # Trigger refresh of the workflow details section
        if workflow_data:
            workflow_details_container.content = create_workflow_details_section(workflow_data)
        page.update()

    def show_pending_analysis_dialog(e):
        """Show detailed pending analysis in a dialog"""
        if not current_active_ticket_data:
            show_message("No ticket data available", error=True)
            return
        
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        # Get comprehensive analysis if available
        comprehensive = current_active_ticket_data.get('comprehensive_ticket_analysis', {})
        
        if comprehensive:
            main_ticket = comprehensive.get('main_ticket', {})
            pending_info = main_ticket.get('pending_from', {})
            
            details_content = ft.Column([
                ft.Text("Detailed Pending Analysis", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                ft.Text("Pending Analysis", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                ft.Text(f"Status-based: {pending_info.get('status_based', 'N/A')}", size=12),
                ft.Text(f"Content-based: {pending_info.get('content_based', 'N/A')}", size=12),
                ft.Text(f"Confidence: {pending_info.get('confidence', 0):.0%}", size=12),
                
                ft.Text("Evidence", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                ft.Column([
                    ft.Text(f"• {evidence}", size=11) 
                    for evidence in pending_info.get('evidence', [])
                ]),
                
                ft.Text("Key Information Found", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                ft.Column([
                    ft.Row([
                        ft.Text(f"{k.replace('_', ' ').title()}:", size=11, weight=ft.FontWeight.BOLD, expand=1),
                        ft.Text(f"{len(v)} items" if isinstance(v, list) else str(v), size=11, expand=2),
                    ]) for k, v in main_ticket.get('key_information', {}).items() if v
                ]),
                
                *([
                    ft.Text("Child Tickets", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                    ft.Column([
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"#{child.get('ticket_id')}", size=11, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{child.get('status', {}).get('display', 'Unknown')}", size=10),
                                ft.Text(f"Pending: {child.get('pending_from', {}).get('content_based', 'Unknown')}", size=10),
                            ]),
                            bgcolor=SECONDARY_BG_COLOR,
                            padding=5,
                            border_radius=3,
                            margin=2
                        ) for child in comprehensive.get('child_tickets', [])[:5]
                    ])
                ] if comprehensive.get('child_tickets') else []),
                
            ], scroll=ft.ScrollMode.AUTO, spacing=10)
        else:
            details_content = ft.Column([
                ft.Text("Basic Pending Information", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text(f"Pending From: {current_active_ticket_data.get('pending_from', 'Unknown')}", size=12),
                ft.Text(f"Confidence: {current_active_ticket_data.get('pending_confidence', 0):.0%}", size=12),
                ft.Text("Evidence:", size=12, weight=ft.FontWeight.BOLD),
                ft.Column([
                    ft.Text(f"• {evidence}", size=11) 
                    for evidence in current_active_ticket_data.get('pending_evidence', [])
                ]),
            ], spacing=10)

        dialog = ft.AlertDialog(
            title=ft.Text("Pending Status Analysis"),
            content=ft.Container(
                content=details_content,
                width=600,
                height=500,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
            ],
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    def create_document_card(doc_analysis: dict) -> ft.Container:
        """Create a card showing document analysis results"""
        doc_type = doc_analysis.get('document_type', 'Unknown')
        category = doc_analysis.get('category', 'Unknown')
        confidence = doc_analysis.get('confidence', 0)
        filename = doc_analysis.get('filename', 'Document')

        category_colors = {
            'identity': ft.Colors.BLUE_ACCENT_400,
            'financial': ft.Colors.GREEN_ACCENT_400,
            'insurance': ft.Colors.PURPLE_ACCENT_400,
            'vehicle': ft.Colors.ORANGE_ACCENT_400,
            'medical': ft.Colors.RED_ACCENT_400,
            'legal': ft.Colors.AMBER_ACCENT_400,
            'kyc': ft.Colors.TEAL_ACCENT_400,
            'claim_supporting': ft.Colors.INDIGO_ACCENT_400
        }

        card_color = category_colors.get(category, ft.Colors.GREY_600)

        quality = doc_analysis.get('quality_assessment', {})
        quality_icons = []

        if quality.get('is_readable', True):
            quality_icons.append(ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=ft.Colors.GREEN_400))
        else:
            quality_icons.append(ft.Icon(ft.Icons.ERROR, size=16, color=ft.Colors.RED_400))

        extracted_data = doc_analysis.get('extracted_data', {})
        data_preview = []
        for key, value in list(extracted_data.items())[:3]:
            data_preview.append(
                ft.Text(
                    f"{key.replace('_', ' ').title()}: {value}",
                    size=10,
                    color=ft.Colors.GREY_300
                )
            )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=24, color=card_color),
                    ft.Column([
                        ft.Text(filename, size=12, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_PRIMARY),
                        ft.Text(f"{doc_type} ({category})", size=10, color=card_color),
                    ], spacing=2, expand=True),
                    ft.Container(
                        content=ft.Text(f"{confidence:.0%}", size=10, color=ft.Colors.WHITE),
                        bgcolor=card_color,
                        padding=5,
                        border_radius=5
                    ),
                ]),
                ft.Divider(height=10, color=ft.Colors.WHITE10),
                ft.Row(quality_icons + [
                    ft.Text(
                        "Quality OK" if quality.get('is_readable', True) else "Quality Issues",
                        size=10,
                        color=ft.Colors.GREY_400
                    )
                ], spacing=5),
                ft.Column(data_preview, spacing=2) if data_preview else ft.Container(),
                ft.Container(height=5),
                ft.Row([
                    ft.TextButton(
                        "View Details",
                        icon=ft.Icons.INFO_OUTLINE,
                        icon_color=card_color,
                        on_click=lambda e, analysis=doc_analysis: show_document_details(analysis)
                    ),
                    ft.TextButton(
                        "Re-analyze",
                        icon=ft.Icons.REFRESH,
                        icon_color=card_color,
                        on_click=lambda e, analysis=doc_analysis: reanalyze_document(analysis)
                    ),
                ], spacing=5),
            ], spacing=5),
            bgcolor=ft.Colors.with_opacity(0.1, card_color),
            padding=15,
            border_radius=8,
            border=ft.border.all(1, card_color),
        )

    def show_document_details(doc_analysis: dict):
        """Show detailed document analysis in a dialog"""
        def close_dialog(e):
            dialog.open = False
            page.update()

        details_content = ft.Column([
            ft.Text(f"Document: {doc_analysis.get('filename', 'Unknown')}", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(),

            ft.Text("Classification", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
            ft.Text(f"Type: {doc_analysis.get('document_type', 'Unknown')}", size=12),
            ft.Text(f"Category: {doc_analysis.get('category', 'Unknown')}", size=12),
            ft.Text(f"Confidence: {doc_analysis.get('confidence', 0):.0%}", size=12),

            ft.Text("Extracted Data", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(k.replace('_', ' ').title() + ":", size=11, weight=ft.FontWeight.BOLD, expand=1),
                        ft.Text(str(v), size=11, expand=2),
                    ]) for k, v in doc_analysis.get('extracted_data', {}).items()
                ], spacing=5),
                bgcolor=SECONDARY_BG_COLOR,
                padding=10,
                border_radius=5,
            ),

            ft.Text("Quality Assessment", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
            ft.Column([
                ft.Row([
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if doc_analysis.get('quality_assessment', {}).get('is_readable', True)
                        else ft.Icons.ERROR,
                        size=16,
                        color=ft.Colors.GREEN_400 if doc_analysis.get('quality_assessment', {}).get('is_readable', True)
                        else ft.Colors.RED_400
                    ),
                    ft.Text(issue, size=11)
                ]) for issue in doc_analysis.get('quality_assessment', {}).get('issues', ['No issues'])
            ], spacing=3),

            *([
                ft.Text("Detected Labels", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                ft.Wrap([
                    ft.Container(
                        content=ft.Text(label['description'], size=10),
                        bgcolor=ft.Colors.BLUE_GREY_800,
                        padding=5,
                        border_radius=3,
                        margin=2
                    ) for label in doc_analysis.get('labels', [])[:10]
                ])
            ] if doc_analysis.get('labels') else []),
        ], scroll=ft.ScrollMode.AUTO, spacing=10)

        dialog = ft.AlertDialog(
            title=ft.Text("Document Analysis Details"),
            content=ft.Container(
                content=details_content,
                width=500,
                height=600,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
            ],
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    def reanalyze_document(doc_analysis: dict):
        """Trigger re-analysis of a document"""
        show_message("Re-analyzing document...")
    
    def upload_document_dialog():
        """Show dialog to upload additional documents"""
        def pick_files_result(e: ft.FilePickerResultEvent):
            if e.files:
                selected_files.value = ", ".join([f.name for f in e.files])
                upload_button.disabled = False
            else:
                selected_files.value = "No files selected"
                upload_button.disabled = True
            page.update()

        def upload_files(e):
            dialog.open = False
            page.update()
            show_message(f"Uploading {len(file_picker.result.files)} files...")

        def close_dialog(e):
            dialog.open = False
            page.update()

        file_picker = ft.FilePicker(on_result=pick_files_result)
        page.overlay.append(file_picker)

        selected_files = ft.Text("No files selected")
        upload_button = ft.ElevatedButton(
            "Upload",
            icon=ft.Icons.UPLOAD,
            disabled=True,
            on_click=upload_files
        )

        dialog = ft.AlertDialog(
            title=ft.Text("Upload Documents"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Select documents to upload:", size=14),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "Choose Files",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=lambda _: file_picker.pick_files(allow_multiple=True)
                    ),
                    ft.Container(height=10),
                    selected_files,
                    ft.Container(height=10),
                    ft.Text("Supported formats: PDF, JPG, PNG, JPEG", size=12, color=ft.Colors.GREY_400),
                ]),
                width=400,
                height=200,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                upload_button,
            ],
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    def request_missing_documents(missing_docs: list):
        """Generate and send request for missing documents"""
        show_message("Generating document request...")

    def display_autonomous_actions(result_data: dict):
        """Display autonomous actions with enhanced workflow progress."""
        actions_list.controls.clear()

        actions = result_data.get('autonomous_actions', [])
        if not actions:
            actions_list.controls.append(
                ft.Text(
                    "No autonomous actions available for this ticket",
                    color=ft.Colors.GREY_400,
                    size=14,
                    text_align=ft.TextAlign.CENTER
                )
            )
        else:
            for action in actions:
                action_card = create_action_card(action)
                action_card.data = action

                if not action_card.content.controls[-1].controls[0].disabled:
                    action_card.content.controls[-1].controls[0].on_click = (
                        lambda e, a=action: execute_action_sync(a)
                    )

                actions_list.controls.append(action_card)

        workflow = result_data.get('workflow', {})
        if workflow and not workflow.get('ticket_id'):
            workflow['ticket_id'] = result_data.get('Ticket ID', '')

        if workflow and 'sop_steps' in workflow:
            workflow_details_container.content = create_workflow_details_section(workflow)
        else:
            workflow_progress.value = 0
            workflow_status_text.value = "No active workflow"
            workflow_progress.color = ft.Colors.GREY_800
            workflow_details_container.content = None

        page.update()

    def execute_action_sync(action: dict):
        """Execute an autonomous action"""
        if not autonomous_action_system:
            show_message("Autonomous action system not available", error=True)
            return

        progressbar.visible = True
        progressbar.value = None
        page.update()

        def handle_execution_result(future):
            """Handle the result of action execution in a thread-safe way"""
            try:
                result = future.result()
                
                def update_result():
                    try:
                        if result.get('success'):
                            show_message(f"Action executed: {result.get('message')}")
                            asyncio.create_task(on_search_click_enhanced(None))
                        else:
                            show_message(f"Action failed: {result.get('message', 'Unknown')}", error=True)
                    except Exception:
                        show_message("Error processing action result", error=True)
                    finally:
                        progressbar.visible = False
                        page.update()
                
                page.run_thread(update_result)
                
            except Exception:
                def update_error():
                    show_message("Error executing action. Please try again.", error=True)
                    progressbar.visible = False
                    page.update()
                
                page.run_thread(update_error)

        def execute_action():
            return autonomous_action_system.execute_action(action)
        
        future = executor.submit(execute_action)
        future.add_done_callback(handle_execution_result)
    
    def on_back_to_placeholder():
        global current_active_ticket_data, active_workflow_id, workflow_step_status
        current_active_ticket_data = None
        active_workflow_id = None
        workflow_step_status = {}

        rca_output_column.controls.clear()
        rca_output_column.controls.extend([
            ft.Text(
                "ID Brain - Autonomous Edition",
                size=24,
                weight=ft.FontWeight.BOLD,
                color=TEXT_COLOR_ACCENT
            ),
            ft.Icon(ft.Icons.SMART_TOY, size=60, color=TEXT_COLOR_ACCENT),
            ft.Text(
                "Enter a Ticket ID to see AI-powered analysis and recommendations.",
                color=TEXT_COLOR_PRIMARY,
                size=12,
                text_align=ft.TextAlign.CENTER,
                italic=True
            )
        ])

        search_entry.value = ""
        search_entry.disabled = False
        search_button.disabled = False
        back_button.visible = False

        # Reset all cards
        ticket_details_card.data.value = "ID:\nSubject:"
        ticket_status_card.data.value = "N/A"
        assigned_to_card.data.value = "Unassigned"
        actions_taken_card.data.value = "No actions logged"
        pending_status_card.data.value = "Analyzing..."
        pending_confidence_card.data.value = "N/A"
        pending_confidence_card.bgcolor = SECONDARY_BG_COLOR
        child_tickets_card.data.value = "None"
        timing_info_card.data.value = "N/A"
        next_action_card.data.value = "N/A"
        prediction_card.data.value = "No predictions yet"
        automation_score_card.data.value = "N/A"
        automation_score_card.bgcolor = SECONDARY_BG_COLOR
        risk_assessment_card.data.value = "No assessment yet"
        next_best_action_card.data.value = "Processing..."
        routing_status_card.data.value = "No routing info"
        current_action_card.data.value = "Processing..."

        # Clear actions list
        actions_list.controls.clear()
        workflow_progress.value = 0
        workflow_status_text.value = "No active workflow"
        workflow_details_container.content = None

        # Clear document section
        document_analysis_card.data.value = "No documents analyzed"
        document_cards_list.controls.clear()

        # Clear suggested response field
        suggested_response_field.value = ""
        send_response_button.disabled = True

        # Clear chat messages
        chat_messages_column.controls.clear()

        page.update()

    async def on_search_click_enhanced(e):
        """Enhanced search with document analysis"""
        global current_active_ticket_data, active_workflow_id

        ticket_id_str = search_entry.value.strip()
        if not ticket_id_str.isdigit():
            show_message("Please enter a valid numerical Ticket ID.", error=True)
            return

        search_button.disabled = True
        search_entry.disabled = True
        progressbar.value = None
        progressbar.visible = True
        page.update()

        result_data = None
        try:
            # 1) Fetch the basic ticket data
            future = executor.submit(process_ticket_id_enhanced, ticket_id_str)
            result_data = await asyncio.wrap_future(future)

            if 'error' in result_data:
                show_message(f"Error: {result_data['error']}", error=True)
                on_back_to_placeholder()
                return

            current_active_ticket_data = result_data

            # 2) Track workflow ID if present
            if 'workflow' in result_data:
                active_workflow_id = result_data['workflow'].get('id')

            # 3) Inject comprehensive routing & action analysis
            try:
                full_ctx = analyze_ticket_comprehensively(int(ticket_id_str))
                result_data['routing_analysis'] = full_ctx.get('routing_analysis', {})
                result_data['action_analysis']  = full_ctx.get('action_analysis', {})
            except Exception as ex:
                print(f"Error merging comprehensive analysis: {ex}")

            # 4) Update the UI
            display_rca_result_enhanced(result_data)
            update_info_cards_enhanced(result_data)
            display_autonomous_actions(result_data)

            # 5) If there are attachments, analyze them too
            if result_data.get('attachments'):
                show_message("Analyzing attached documents...")
                future_docs = executor.submit(
                    process_ticket_attachments_enhanced,
                    current_active_ticket_data
                )
                try:
                    updated_data = await asyncio.wrap_future(future_docs)
                    current_active_ticket_data.update(updated_data)
                    display_autonomous_actions_with_documents(current_active_ticket_data)
                except Exception as ex:
                    print(f"Document analysis error: {ex}")

            # 6) Populate suggested response if available
            suggested = result_data.get('suggested_response', '')
            if suggested:
                suggested_response_field.value = suggested
                send_response_button.disabled = False
            else:
                suggested_response_field.value = ""
                send_response_button.disabled = True

            # 7) Finalize progress
            progressbar.value = 1
            if result_data.get('autonomous_actions'):
                action_count = len(result_data['autonomous_actions'])
                show_message(
                    f"Analysis complete! Found {action_count} recommended actions. "
                    f"Check the 'Autonomous Actions' tab."
                )
            else:
                show_message(f"Successfully processed ticket {ticket_id_str}!")

        except Exception as ex:
            print(f"Exception in search: {type(ex).__name__}: {ex}")
            traceback.print_exc()
            show_message(f"Critical Error: {type(ex).__name__} - {ex}", error=True)
            on_back_to_placeholder()

        finally:
            # Reset buttons & hide progressbar
            search_button.disabled = False
            search_entry.disabled = False
            progressbar.visible = False
            page.update()


    def add_message_to_chat(sender: str, message: str, is_user: bool = False, is_action: bool = False):
        align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
        color = (
            ft.Colors.BLUE_GREY_700 if is_user
            else (ft.Colors.PURPLE_900 if is_action else SECONDARY_BG_COLOR)
        )
        text_align = ft.TextAlign.RIGHT if is_user else ft.TextAlign.LEFT

        chat_messages_column.controls.append(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row([
                                    ft.Icon(
                                        ft.Icons.SMART_TOY if is_action else None,
                                        size=16,
                                        color=ft.Colors.PURPLE_400
                                    ) if not is_user else ft.Container(),
                                    ft.Text(
                                        sender,
                                        size=10,
                                        color=ft.Colors.GREY,
                                        text_align=text_align
                                    ),
                                ]),
                                ft.Text(
                                    message,
                                    size=14,
                                    color=TEXT_COLOR_PRIMARY,
                                    selectable=True,
                                    max_lines=None
                                ),
                            ],
                            horizontal_alignment=(
                                ft.CrossAxisAlignment.END if is_user
                                else ft.CrossAxisAlignment.START
                            ),
                            spacing=2,
                        ),
                        padding=10,
                        border_radius=ft.border_radius.all(10),
                        bgcolor=color,
                        width=page.width * 0.7,
                    )
                ],
                alignment=align,
            )
        )
        page.update()

        def scroll_to_bottom():
            try:
                if hasattr(chat_messages_column, 'scroll_to'):
                    chat_messages_column.scroll_to(
                        offset=-1,
                        duration=300
                    )
            except:
                pass
            page.update()

        page.run_thread(scroll_to_bottom)

    async def send_chat_message(e):
        user_message = chat_input_field.value.strip()
        chat_input_field.value = ""
        send_chat_button.disabled = True
        chat_input_field.disabled = True
        page.update()

        if user_message:
            add_message_to_chat("You", user_message, is_user=True)

            progressbar.value = None
            progressbar.visible = True
            page.update()

            ai_response = ""
            try:
                if current_active_ticket_data is None:
                    ai_response = (
                        "I need a Freshdesk ticket to answer questions. "
                        "Please go to the 'ID Brain (RCA)' tab, enter a Ticket ID, and click 'Search' first."
                    )
                else:
                    action_keywords = [
                        'next step', 'what should i do', 'action',
                        'recommend', 'suggestion', 'automate'
                    ]
                    is_action_query = any(
                        keyword in user_message.lower() for keyword in action_keywords
                    )

                    ticket_content_for_qa = (
                        f"Ticket ID: {current_active_ticket_data.get('Ticket ID', 'N/A')}\n"
                        f"Subject: {current_active_ticket_data.get('Subject', '')}\n"
                        f"Problem: {current_active_ticket_data.get('Problem', '')}\n"
                        f"Why: {current_active_ticket_data.get('Why', '')}\n"
                        f"Solution: {current_active_ticket_data.get('Solution', '')}\n"
                        f"Classification: {current_active_ticket_data.get('Classification', '')}\n"
                        f"SOP Category: {current_active_ticket_data.get('sop_category', '')}\n"
                        f"Status: {status_map.get(current_active_ticket_data.get('status'), 'Unknown')}\n"
                        f"Full Ticket Content: {current_active_ticket_data.get('raw_ticket_content', '')}"
                    )

                    future = executor.submit(
                        get_enhanced_claude_answer,
                        ticket_content_for_qa,
                        user_message,
                        current_active_ticket_data if is_action_query else None
                    )
                    ai_response = await asyncio.wrap_future(future)

                add_message_to_chat(
                    "ID Brain AI",
                    ai_response,
                    is_user=False,
                    is_action=is_action_query
                )
            except Exception as ex:
                add_message_to_chat(
                    "ID Brain AI",
                    f"Error: Could not get a response. ({type(ex).__name__}: {ex})",
                    is_user=False
                )
                traceback.print_exc()
            finally:
                progressbar.visible = False
                progressbar.value = 0
                send_chat_button.disabled = False
                chat_input_field.disabled = False
                chat_input_field.focus()
                page.update()

    async def send_suggested_response(e):
        """Send the suggested response via Freshdesk API."""
        response_text = suggested_response_field.value.strip()
        if not response_text:
            show_message("No response to send", error=True)
            return

        show_message("Response sent successfully! (Simulated)")
        send_response_button.disabled = True
        page.update()

    def copy_suggested_response(e):
        """Copy suggested response to clipboard."""
        page.set_clipboard(suggested_response_field.value)
        show_message("Response copied to clipboard!")

    def display_autonomous_actions_with_documents(result_data: dict):
        """Display autonomous actions with document analysis"""
        display_autonomous_actions(result_data)

        if 'attachment_analysis' in result_data:
            analysis = result_data['attachment_analysis']

            doc_summary_parts = []

            total = analysis.get('total_attachments', 0)
            if total > 0:
                doc_summary_parts.append(f"Total Documents: {total}")

                if analysis.get('document_summary'):
                    for category, files in analysis['document_summary'].items():
                        doc_summary_parts.append(f"\n{category.title()}: {len(files)}")

                if analysis.get('missing_documents'):
                    doc_summary_parts.append(f"\n⚠️ Missing: {len(analysis['missing_documents'])}")

                if analysis.get('quality_issues'):
                    doc_summary_parts.append(f"\n⚠️ Quality Issues: {len(analysis['quality_issues'])}")
            else:
                doc_summary_parts.append("No documents found")

            document_analysis_card.data.value = "\n".join(doc_summary_parts)

            document_cards_list.controls.clear()

            for doc in analysis.get('analyzed', []):
                doc_card = create_document_card(doc)
                document_cards_list.controls.append(doc_card)

            if analysis.get('missing_documents'):
                missing_docs_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.WARNING, size=20, color=ft.Colors.ORANGE_400),
                            ft.Text("Missing Required Documents", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_400),
                        ]),
                        ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.CIRCLE, size=8, color=ft.Colors.ORANGE_400),
                                ft.Text(doc, size=11, color=TEXT_COLOR_PRIMARY),
                            ]) for doc in analysis['missing_documents']
                        ], spacing=3),
                        ft.ElevatedButton(
                            "Request Documents",
                            icon=ft.Icons.EMAIL,
                            bgcolor=ft.Colors.ORANGE_400,
                            color=ft.Colors.WHITE,
                            on_click=lambda e: request_missing_documents(analysis['missing_documents'])
                        )
                    ], spacing=8),
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.ORANGE_400),
                    padding=15,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.ORANGE_400),
                )
                document_cards_list.controls.insert(0, missing_docs_card)

            page.update()

    def analyze_all_documents():
        """Trigger analysis of all documents in the current ticket"""
        if not current_active_ticket_data:
            show_message("Please load a ticket first", error=True)
            return

        progressbar.visible = True
        progressbar.value = None
        page.update()

        def handle_analysis_result(future):
            """Handle the result of the analysis in a thread-safe way"""
            try:
                result = future.result()
                
                def update_success():
                    try:
                        display_autonomous_actions_with_documents(result)
                        current_active_ticket_data.update(result)
                        show_message("Document analysis complete!")
                    except Exception as ui_err:
                        show_message("Error updating UI after document analysis", error=True)
                    finally:
                        progressbar.visible = False
                        page.update()
                
                page.run_thread(update_success)
                
            except Exception as analysis_err:
                def update_error():
                    show_message("Error analyzing documents. Please try again.", error=True)
                    progressbar.visible = False
                    page.update()
                
                page.run_thread(update_error)

        try:
            future = executor.submit(process_ticket_attachments_enhanced, current_active_ticket_data)
            future.add_done_callback(handle_analysis_result)
            
        except Exception as submit_err:
            show_message(f"Error starting document analysis: {submit_err}", error=True)
            progressbar.visible = False
            page.update()

    def create_action_card(action: dict) -> ft.Container:
        """Create a card for displaying an autonomous action."""
        priority = action.get('priority', 'MEDIUM')
        color = PRIORITY_COLORS.get(priority, ft.Colors.BLUE_ACCENT_400)

        can_execute = action.get('auto_executable', False)

        execute_button = ft.ElevatedButton(
            "Execute",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=color,
            color=ft.Colors.WHITE,
            disabled=not can_execute,
            data=action
        )

        checklist_items = []
        if 'checklist' in action:
            for item in action['checklist']:
                checklist_items.append(
                    ft.Row([
                        ft.Checkbox(value=False),
                        ft.Text(item, size=11, color=TEXT_COLOR_PRIMARY)
                    ])
                )

        content_column = [
            ft.Row([
                ft.Icon(
                    ft.Icons.PRIORITY_HIGH if priority == 'HIGH' else ft.Icons.INFO,
                    size=20,
                    color=color
                ),
                ft.Text(
                    action.get('type', 'ACTION'),
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=color
                ),
                ft.Container(expand=True),
                ft.Text(priority, size=10, color=color)
            ]),
            ft.Text(action.get('action', ''), size=13, color=TEXT_COLOR_PRIMARY, weight=ft.FontWeight.BOLD),
            ft.Text(f"Reason: {action.get('reason', '')}", size=11, color=ft.Colors.GREY_400),
        ]

        if checklist_items:
            content_column.append(ft.Column(checklist_items, spacing=2))

        if 'deadline' in action:
            deadline = action['deadline']
            if isinstance(deadline, datetime):
                deadline_str = deadline.strftime("%Y-%m-%d %H:%M")
            else:
                deadline_str = str(deadline)
            content_column.append(ft.Text(f"Deadline: {deadline_str}", size=10, color=ft.Colors.ORANGE_400))

        content_column.append(
            ft.Row([execute_button], alignment=ft.MainAxisAlignment.END)
        )

        return ft.Container(
            content=ft.Column(content_column, spacing=5),
            bgcolor=ft.Colors.with_opacity(0.1, color),
            padding=15,
            border_radius=8,
            border=ft.border.all(1, color),
            animate=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT)
        )

    def display_rca_result_enhanced(result_data: dict):
        """Enhanced display with autonomous features."""
        rca_output_column.controls.clear()

        def create_rca_section(title: str, content: str, icon_name: str = None):
            return ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon_name, size=20, color=TEXT_COLOR_ACCENT) if icon_name else ft.Container(),
                            ft.Text(
                                title,
                                font_family=TEXT_FONT,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_COLOR_ACCENT
                            ),
                        ],
                        spacing=5,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Container(
                        content=ft.Text(
                            content if content else "N/A",
                            font_family=TEXT_FONT,
                            size=12,
                            color=TEXT_COLOR_PRIMARY,
                            selectable=True,
                            max_lines=None,
                            text_align=ft.TextAlign.LEFT,
                        ),
                        padding=10,
                        border_radius=5,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE10),
                        expand=True,
                    ),
                ],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.START,
                expand=True,
            )

        rca_output_column.controls.append(create_rca_section("Problem", result_data.get("Problem"), ft.Icons.ERROR_OUTLINE))
        rca_output_column.controls.append(create_rca_section("Why", result_data.get("Why"), ft.Icons.HELP_OUTLINE))
        rca_output_column.controls.append(create_rca_section("Solution", result_data.get("Solution"), ft.Icons.LIGHTBULB_OUTLINE))
        rca_output_column.controls.append(create_rca_section("Classification", result_data.get("Classification"), ft.Icons.CATEGORY_OUTLINED))
        rca_output_column.controls.append(create_rca_section("Cluster", result_data.get("Cluster"), ft.Icons.GROUP_WORK_OUTLINED))

        if 'sop_category' in result_data:
            rca_output_column.controls.append(create_rca_section("SOP Category", result_data.get("sop_category"), ft.Icons.RULE))

        ticket_url = result_data.get("ticket_url")
        if ticket_url and ticket_url != "#":
            rca_output_column.controls.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.LINK, size=20, color=TEXT_COLOR_ACCENT),
                        ft.Text(
                            "View Ticket: ",
                            font_family=TEXT_FONT,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_COLOR_ACCENT
                        ),
                        ft.Markdown(
                            f"[{ticket_url}]({ticket_url})",
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            on_tap_link=lambda e: page.launch_url(e.data)
                        )
                    ],
                    spacing=5,
                    alignment=ft.MainAxisAlignment.START,
                )
            )

        back_button.visible = True
        
        routing_text = "N/A" 
        if 'routing_analysis' in result_data:
            routing = result_data['routing_analysis']
            routing_text = f"Primary Intent: {routing.get('primary_intent', 'N/A')}\n"
            routing_text += f"Current Routing: {routing.get('current_routing', 'N/A')}\n"
            
            if routing.get('routing_history'):
                history = routing['routing_history']
                recent_routes = history[-3:] if len(history) > 3 else history
                routing_text += "\nRecent Routing:\n"
                for route in recent_routes:
                    routing_text += f"• {route.get('routed_to', 'Unknown')} - {route.get('reason', 'N/A')}\n"
        
        rca_output_column.controls.append(
            create_rca_section("Routing Analysis", routing_text, ft.Icons.ROUTE)
        )
    
        action_text = "N/A"
        if 'action_analysis' in result_data:
            action = result_data['action_analysis']
            action_text = f"Current: {action.get('current_action', 'N/A')}\n"
            
            if action.get('next_steps'):
                action_text += "\nNext Steps:\n"
                for step in action['next_steps'][:3]:
                    action_text += f"• {step.get('action', 'N/A')} ({step.get('priority', 'N/A')})\n"
        
        rca_output_column.controls.append(
            create_rca_section("Action Status", action_text, ft.Icons.PENDING_ACTIONS)
        )

        page.update()

    def update_info_cards_enhanced(result_data: dict):
        """Update info cards with enhanced data and pending status information."""
        ticket_id = result_data.get("Ticket ID", "N/A")
        subject = result_data.get("Subject", "N/A")

        ticket_status_id = result_data.get("status")
        human_readable_status = status_map.get(ticket_status_id, f"Unknown ({ticket_status_id})")

        assignee_name = result_data.get("Assignee")
        if assignee_name and assignee_name not in ["N/A (Backend Missing)", "N/A (Wrapper Default)"]:
            assigned_to_display = assignee_name
        else:
            agent_id = result_data.get("agent_id")
            if agent_id:
                assigned_to_display = f"ID: {agent_id} (Name N/A)"
            else:
                assigned_to_display = "Unassigned"

        ticket_details_card.data.value = f"ID: {ticket_id}\nSubject: {subject}"
        ticket_status_card.data.value = human_readable_status
        assigned_to_card.data.value = assigned_to_display
        actions_taken_card.data.value = result_data.get("Actions Taken", "No actions logged")

        pending_from = result_data.get('pending_from', 'Unknown')
        pending_confidence = result_data.get('pending_confidence', 0)
        pending_evidence = result_data.get('pending_evidence', [])
        
        pending_status_text = f"Pending from: {pending_from.title()}\n"
        if pending_evidence:
            pending_status_text += f"Evidence:\n"
            for evidence in pending_evidence[:3]:
                pending_status_text += f"• {evidence}\n"
        
        pending_status_card.data.value = pending_status_text
        
        confidence_percentage = f"{pending_confidence:.0%}" if pending_confidence else "N/A"
        pending_confidence_card.data.value = confidence_percentage
        
        if pending_confidence >= 0.8:
            pending_confidence_card.bgcolor = ft.Colors.GREEN_900
        elif pending_confidence >= 0.5:
            pending_confidence_card.bgcolor = ft.Colors.ORANGE_900
        elif pending_confidence > 0:
            pending_confidence_card.bgcolor = ft.Colors.RED_900
        else:
            pending_confidence_card.bgcolor = SECONDARY_BG_COLOR

        if result_data.get('child_summary'):
            child_summary = result_data['child_summary']
            child_text = f"Total: {len(child_summary)} child tickets\n"
            
            for child in child_summary[:3]:
                child_text += f"• #{child['ticket_id']}: {child['status']}\n"
                child_text += f"  Pending: {child['pending_from']}\n"
            
            if len(child_summary) > 3:
                child_text += f"... and {len(child_summary) - 3} more"
                
            child_tickets_card.data.value = child_text
        elif result_data.get('child_tickets'):
            child_tickets = result_data['child_tickets']
            child_text = f"Total: {len(child_tickets)} child tickets\n"
            for child in child_tickets[:3]:
                child_text += f"• #{child.get('id')}: {child.get('subject', 'N/A')[:30]}...\n"
            child_tickets_card.data.value = child_text
        else:
            child_tickets_card.data.value = "No child tickets"

        timing_info = result_data.get('timing_info', {})
        if timing_info and 'error' not in timing_info:
            timing_text = f"Age: {timing_info.get('age_days', 0):.1f} days\n"
            
            hours_since_update = timing_info.get('hours_since_last_update')
            if hours_since_update:
                timing_text += f"Last update: {hours_since_update:.1f}h ago\n"
            
            hours_since_customer = timing_info.get('hours_since_last_customer_message')
            if hours_since_customer:
                timing_text += f"Customer msg: {hours_since_customer:.1f}h ago\n"
            
            business_hours = timing_info.get('business_hours_age')
            if business_hours:
                timing_text += f"Business hours: {business_hours}h"
                
            timing_info_card.data.value = timing_text
        else:
            timing_info_card.data.value = "Timing info unavailable"

        next_action = result_data.get('next_expected_action', {})
        if next_action and isinstance(next_action, dict):
            action_text = f"Action: {next_action.get('action', 'N/A')}\n"
            action_text += f"Priority: {next_action.get('priority', 'N/A')}\n"
            action_text += f"Timeline: {next_action.get('timeline', 'N/A')}\n"
            action_text += f"Details: {next_action.get('details', 'N/A')[:50]}..."
            next_action_card.data.value = action_text
        else:
            next_action_card.data.value = "No specific action recommended"

        predictions = result_data.get('predictions', {})
        if predictions:
            escalation_risk = predictions.get('escalation_risk', 0)
            resolution_time = predictions.get('estimated_resolution_time', {})
            satisfaction_risk = predictions.get('customer_satisfaction_risk', 0)

            pred_text = f"Escalation Risk: {escalation_risk}%\n"
            if isinstance(resolution_time, dict) and 'display' in resolution_time:
                pred_text += f"Est. Resolution: {resolution_time['display']}\n"
            elif isinstance(resolution_time, dict) and 'hours' in resolution_time:
                pred_text += f"Est. Resolution: {resolution_time['hours']} hrs\n"
            else:
                pred_text += "Est. Resolution: N/A\n"
            pred_text += f"Satisfaction Risk: {satisfaction_risk}%"
            prediction_card.data.value = pred_text
        else:
            prediction_card.data.value = "No predictions yet"

        if predictions and 'automation_potential' in predictions:
            score = predictions['automation_potential']
            automation_score_card.data.value = f"{score:.0%}"
            if score > 0.7:
                automation_score_card.bgcolor = ft.Colors.GREEN_900
            elif score > 0.4:
                automation_score_card.bgcolor = ft.Colors.ORANGE_900
            else:
                automation_score_card.bgcolor = ft.Colors.RED_900
        else:
            automation_score_card.data.value = "N/A"
            automation_score_card.bgcolor = SECONDARY_BG_COLOR

        if predictions:
            risk_text = []
            if predictions.get('escalation_risk', 0) > 70:
                risk_text.append("⚠️ High escalation risk")
            if predictions.get('customer_satisfaction_risk', 0) > 60:
                risk_text.append("⚠️ Customer satisfaction at risk")
            if not risk_text:
                risk_text.append("✓ Low risk profile")
            risk_assessment_card.data.value = "\n".join(risk_text)
        else:
            risk_assessment_card.data.value = "No assessment yet"

        if result_data.get('autonomous_actions'):
            next_action = result_data['autonomous_actions'][0]
            next_best_action_card.data.value = f"➤ {next_action.get('action', 'No action')}\n   Priority: {next_action.get('priority', 'N/A')}"
        else:
            next_best_action_card.data.value = "No recommended actions"

        routing_text = "N/A"
        if 'routing_analysis' in result_data:
            routing = result_data['routing_analysis']
            routing_text = f"Primary intent: {routing.get('primary_intent', 'Unknown')}\n"
            routing_text += f"Current routing: {routing.get('current_routing', 'N/A')}"
        routing_status_card.data.value = routing_text

        action_text = "N/A"
        if 'action_analysis' in result_data:
            action = result_data['action_analysis']
            action_text = f"Current: {action.get('current_action', 'Unknown')}\n"
            next_steps = action.get('next_steps', [])
            if next_steps:
                action_text += "Next Steps:\n"
                for step in next_steps[:3]:
                    action_text += f"• {step.get('action', 'N/A')}\n"
        current_action_card.data.value = action_text
        
        summary_text = ""
        if 'executive_summary' in result_data:
            summary_data = result_data['executive_summary']
            if summary_data:
                summary_text = f"\n{summary_data.get('one_line_status', '')}"
        
        ticket_status_card.data.value += summary_text
        
        page.update()

    # --- UI Elements Initialization ---
    # Logo
    logo_image = (
        ft.Image(src=ASSET_ICON_PATH, width=150, height=50, fit=ft.ImageFit.CONTAIN)
        if os.path.exists(FULL_ICON_PATH)
        else ft.Text("InsuranceDekho", size=20, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT)
    )

    logo_button_container = ft.Container(
        content=logo_image,
        on_click=lambda e: show_message("InsuranceDekho ID Brain - Autonomous Edition!"),
        tooltip="InsuranceDekho ID Brain - Autonomous Edition!",
        ink=True,
    )

    progressbar = ft.ProgressBar(value=0, visible=False, color=ft.Colors.BLUE_ACCENT, bgcolor="#EEEEEE")

    # --- RCA Tab UI Elements ---
    rca_output_column = ft.Column(
        controls=[],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    # Info cards with scrollable content for RCA tab
    ticket_details_card = create_info_card("Ticket Details", ft.Icons.CONFIRMATION_NUMBER_OUTLINED, "ID:\nSubject:", scrollable=True)
    ticket_status_card = create_info_card("Status", ft.Icons.INFO_OUTLINE, "N/A", scrollable=True)
    assigned_to_card = create_info_card("Assigned To", ft.Icons.PERSON_OUTLINE, "N/A", scrollable=True)
    actions_taken_card = create_info_card("Actions Taken", ft.Icons.SETTINGS_APPLICATIONS_OUTLINED, "No actions logged", scrollable=True)
    routing_status_card = create_info_card("Routing Status", ft.Icons.ROUTE, "No routing info", scrollable=True)
    current_action_card = create_info_card("Current Action", ft.Icons.PENDING_ACTIONS, "Processing...", scrollable=True)
    
    # NEW ENHANCED PENDING STATUS CARDS
    pending_status_card = create_info_card("Pending Status", ft.Icons.PENDING, "Analyzing...", scrollable=True)
    pending_confidence_card = create_info_card("Confidence", ft.Icons.ANALYTICS, "N/A")
    child_tickets_card = create_info_card("Child Tickets", ft.Icons.ACCOUNT_TREE, "None", scrollable=True)
    timing_info_card = create_info_card("Timing Info", ft.Icons.SCHEDULE, "N/A", scrollable=True)
    next_action_card = create_info_card("Next Action", ft.Icons.NEXT_PLAN, "N/A", scrollable=True)
    
    # Make pending cards clickable for detailed view
    pending_status_card.on_click = show_pending_analysis_dialog
    pending_confidence_card.on_click = show_pending_analysis_dialog
    
    # New cards for autonomous features - for Autonomous Actions tab
    prediction_card = create_info_card("AI Predictions", ft.Icons.INSIGHTS, "No predictions yet", expandable=True, scrollable=True)
    automation_score_card = create_info_card("Automation Score", ft.Icons.SPEED, "N/A",)

    # Additional insight cards
    risk_assessment_card = create_info_card("Risk Assessment", ft.Icons.WARNING, "No assessment yet", expandable=True, scrollable=True)
    next_best_action_card = create_info_card("Next Best Action", ft.Icons.RECOMMEND, "Processing...", expandable=True, scrollable=True)

    # Create document analysis card
    document_analysis_card = create_info_card(
        "Document Analysis",
        ft.Icons.DOCUMENT_SCANNER,
        "No documents analyzed",
        expandable=True,
        scrollable=True
    )

    # Create document cards list container
    document_cards_list = ft.ListView(
        expand=True,
        spacing=10,
        padding=ft.padding.all(10)
    )

    # Search controls
    search_entry = ft.TextField(
        hint_text="Enter Ticket ID...",
        expand=True,
        height=40,
        content_padding=10,
        border_color=TEXT_COLOR_ACCENT,
        focused_border_color=ft.Colors.BLUE_ACCENT,
        bgcolor=PRIMARY_BG_COLOR,
        text_style=ft.TextStyle(font_family=TEXT_FONT, size=14, color=TEXT_COLOR_PRIMARY),
    )

    search_button = ft.IconButton(
        ft.Icons.SEARCH,
        icon_color=TEXT_COLOR_ACCENT,
        tooltip="Search Ticket",
    )

    back_button = ft.ElevatedButton(
        "← Back",
        icon=ft.Icons.ARROW_BACK,
        bgcolor=ft.Colors.BLUE_GREY_700,
        color=ft.Colors.WHITE,
        visible=False
    )

    # --- Autonomous Actions Tab ---
    actions_list = ft.ListView(
        expand=True,
        spacing=10,
        padding=ft.padding.all(10)
    )

    workflow_progress = ft.ProgressBar(
        value=0,
        height=20,
        color=ft.Colors.GREEN_ACCENT_400,
        bgcolor=ft.Colors.GREY_800,
        border_radius=10
    )

    workflow_status_text = ft.Text(
        "No active workflow",
        size=14,
        color=TEXT_COLOR_PRIMARY,
        text_align=ft.TextAlign.CENTER
    )

    # Container for workflow details
    workflow_details_container = ft.Container()

    # Suggested response area (for Chat with AI Tab) - INCREASED SIZE
    suggested_response_field = ft.TextField(
        multiline=True,
        min_lines=8,
        max_lines=12,
        read_only=False,
        border_color=TEXT_COLOR_ACCENT,
        bgcolor=PRIMARY_BG_COLOR,
        text_style=ft.TextStyle(font_family=TEXT_FONT, size=12, color=TEXT_COLOR_PRIMARY),
        hint_text="AI-generated response will appear here..."
    )

    send_response_button = ft.ElevatedButton(
        "Send Response",
        icon=ft.Icons.SEND,
        bgcolor=ft.Colors.GREEN_ACCENT_700,
        color=ft.Colors.WHITE,
        disabled=True
    )

    copy_response_button = ft.IconButton(
        ft.Icons.COPY,
        icon_color=TEXT_COLOR_ACCENT,
        tooltip="Copy to clipboard"
    )

    # --- Chat Tab UI Elements - INCREASED SIZE ---
    chat_messages_column = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        spacing=10,
        controls=[],
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    chat_input_field = ft.TextField(
        hint_text="Type your message... (Try: 'What actions should I take?')",
        expand=True,
        multiline=False,
        max_lines=1,
        content_padding=10,
        border_color=TEXT_COLOR_ACCENT,
        focused_border_color=ft.Colors.BLUE_ACCENT,
        bgcolor=PRIMARY_BG_COLOR,
        text_style=ft.TextStyle(font_family=TEXT_FONT, size=14, color=TEXT_COLOR_PRIMARY),
    )

    send_chat_button = ft.IconButton(
        ft.Icons.SEND,
        icon_color=TEXT_COLOR_ACCENT,
        tooltip="Send Message",
    )

    # --- Attach event handlers ---
    search_entry.on_submit = on_search_click_enhanced
    search_button.on_click = on_search_click_enhanced
    back_button.on_click = lambda e: on_back_to_placeholder()

    chat_input_field.on_submit = send_chat_message
    send_chat_button.on_click = send_chat_message

    send_response_button.on_click = send_suggested_response
    copy_response_button.on_click = copy_suggested_response

    # --- Layout Assembly ---
    # Initialize RCA output with placeholder
    rca_output_column.controls.extend([
        ft.Text(
            "ID Brain - Autonomous Edition",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=TEXT_COLOR_ACCENT
        ),
        ft.Icon(ft.Icons.SMART_TOY, size=60, color=TEXT_COLOR_ACCENT),
        ft.Text(
            "Enter a Ticket ID to see AI-powered analysis and recommendations.",
            color=TEXT_COLOR_PRIMARY,
            size=12,
            text_align=ft.TextAlign.CENTER,
            italic=True
        )
    ])

    # RCA Tab Content - UPDATED with NEW ENHANCED PENDING CARDS
    right_side_cards = ft.Column(
        [
            ticket_details_card,
            ticket_status_card,
            assigned_to_card,
            pending_status_card,
            pending_confidence_card,
            child_tickets_card,
            timing_info_card,
            next_action_card,
            routing_status_card,
            current_action_card,
            actions_taken_card,
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.START,
        scroll=ft.ScrollMode.AUTO,
    )

    # RCA Tab Content with scrollable right side
    rca_main_content_frame = ft.Column(
        [
            ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                rca_output_column,
                                ft.Row([back_button], alignment=ft.MainAxisAlignment.END)
                            ],
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=PRIMARY_BG_COLOR,
                        padding=DEFAULT_PADDING,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE10)),
                        expand=True,
                    ),
                    ft.Container(
                        content=right_side_cards,
                        padding=ft.padding.only(left=DEFAULT_PADDING),
                        bgcolor="#000000",
                        width=200,
                        height=600,
                    )
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
                expand=True,
            ),
        ],
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Autonomous Actions Tab Content - WITH Document Analysis Section
    autonomous_tab_scroll = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Autonomous Actions & Workflow", size=20, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                        ft.Divider(height=20, color=ft.Colors.WHITE10),

                        # Workflow Progress Section
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Workflow Progress", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_PRIMARY),
                                workflow_progress,
                                workflow_status_text,
                            ], spacing=10),
                            padding=15,
                            bgcolor=SECONDARY_BG_COLOR,
                            border_radius=8,
                        ),

                        # Workflow Details (SOP Steps)
                        workflow_details_container,

                        # Actions List
                        ft.Text("Recommended Actions", size=16, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_PRIMARY),
                        ft.Container(
                            content=actions_list,
                            height=400,
                            bgcolor=PRIMARY_BG_COLOR,
                            border_radius=8,
                            border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE10)),
                        ),

                        # Document Analysis Section
                        ft.Text("Document Analysis", size=18, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                        ft.Divider(height=20, color=ft.Colors.WHITE10),

                        ft.Row([
                            document_analysis_card,
                            ft.Container(
                                content=ft.Column([
                                    ft.ElevatedButton(
                                        "Analyze All Documents",
                                        icon=ft.Icons.DOCUMENT_SCANNER,
                                        bgcolor=ft.Colors.BLUE_ACCENT_700,
                                        color=ft.Colors.WHITE,
                                        on_click=lambda e: analyze_all_documents()
                                    ),
                                    ft.ElevatedButton(
                                        "Upload Document",
                                        icon=ft.Icons.UPLOAD_FILE,
                                        bgcolor=ft.Colors.GREEN_ACCENT_700,
                                        color=ft.Colors.WHITE,
                                        on_click=lambda e: upload_document_dialog()
                                    ),
                                ], spacing=10),
                                padding=10,
                            )
                        ], spacing=15),

                        # Document Cards List
                        ft.Text("Analyzed Documents", size=16, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_PRIMARY),
                        ft.Container(
                            content=document_cards_list,
                            height=400,
                            bgcolor=PRIMARY_BG_COLOR,
                            border_radius=8,
                            border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE10)),
                        ),

                        # AI Insights Section
                        ft.Text("AI-Powered Insights", size=18, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_ACCENT),
                        ft.Divider(height=20, color=ft.Colors.WHITE10),

                        # Insights cards in a row
                        ft.Row([
                            prediction_card,
                            automation_score_card,
                        ], spacing=15),

                        ft.Row([
                            risk_assessment_card,
                            next_best_action_card,
                        ], spacing=15),
                    ],
                    spacing=15,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=DEFAULT_PADDING,
            ),
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
    )

    actions_tab_content = ft.Container(
        content=autonomous_tab_scroll,
        expand=True,
    )

    # Chat Tab Content - MAXIMIZED SPACE WITH LARGER AI RESPONSE AREA
    chat_tab_content = ft.Column(
        [
            # Main chat area
            ft.Container(
                content=chat_messages_column,
                expand=True,
                padding=DEFAULT_PADDING,
                bgcolor=SECONDARY_BG_COLOR,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE10)),
            ),

            # Chat input area
            ft.Container(
                content=ft.Row(
                    [
                        chat_input_field,
                        send_chat_button,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=ft.padding.only(left=15, right=15, top=10, bottom=5),
            ),

            # AI-Generated Response Section - MUCH LARGER
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("AI-Generated Response", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR_PRIMARY),
                        ft.Container(expand=True),
                        copy_response_button,
                        send_response_button,
                    ]),
                    suggested_response_field,
                ], spacing=5),
                padding=15,
                bgcolor=PRIMARY_BG_COLOR,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE10)),
                height=250,
            ),
        ],
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
    )

    # --- Main Layout with Tabs ---
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="ID Brain (RCA)",
                icon=ft.Icons.ANALYTICS,
                content=rca_main_content_frame,
            ),
            ft.Tab(
                text="Autonomous Actions",
                icon=ft.Icons.SETTINGS_SUGGEST,
                content=actions_tab_content,
            ),
            ft.Tab(
                text="Chat with AI",
                icon=ft.Icons.CHAT,
                content=chat_tab_content,
            ),
        ],
        expand=True,
    )

    # --- Main Container ---
    main_container = ft.Container(
        content=ft.Column(
            [
                # Header with Logo and Search
                ft.Container(
                    content=ft.Row(
                        [
                            logo_button_container,
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Row(
                                    [search_entry, search_button],
                                    spacing=10,
                                ),
                                width=400,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=PRIMARY_BG_COLOR,
                    padding=DEFAULT_PADDING,
                    border_radius=ft.border_radius.only(top_left=10, top_right=10),
                ),
                progressbar,
                tabs,
            ],
            spacing=0,
            expand=True,
        ),
        bgcolor="#000000",
        expand=True,
    )

    page.add(main_container)
    page.update()


# Run the app
if __name__ == "__main__":
    ft.app(target=main)